// 第 5 轮：真实 8 人混合场景
// 目的：复现真实故障 —— 重任务运行期间，普通用户是否还能正常操作
// 模拟: 6 个普通用户 + 1 个文档上传 + 1 个音频转写
// k6 run round5-mixed.js

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8011";
const K6_USER = __ENV.K6_USER || "admin";
const K6_PASS = __ENV.K6_PASS || "admin123";

const docFile = open("./sample.docx", "b");
const audioFile = open("./sample.mp3", "b");

const extractTaskDuration = new Trend("extract_task_duration", true);
const transcribeTaskDuration = new Trend("transcribe_task_duration", true);
const extractTaskSuccess = new Rate("extract_task_success");
const transcribeTaskSuccess = new Rate("transcribe_task_success");

function login() {
  const body = JSON.stringify({ username: K6_USER, password: K6_PASS });
  const res = http.post(`${BASE_URL}/api/auth/login`, body, {
    headers: { "Content-Type": "application/json" },
    tags: { type: "login" },
  });
  check(res, { "login status 200": (r) => r.status === 200 });
  try { return res.json().token || ""; } catch (e) { return ""; }
}

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function waitForTask(token, taskId, kind) {
  if (!taskId) return false;

  const startedAt = Date.now();
  const timeoutSeconds = parseInt(__ENV.TASK_TIMEOUT_SECONDS) || 1800;
  const pollSeconds = parseInt(__ENV.TASK_POLL_SECONDS) || 3;

  while ((Date.now() - startedAt) / 1000 < timeoutSeconds) {
    const res = http.get(`${BASE_URL}/api/tasks/${taskId}`, {
      headers: authHeaders(token),
      tags: { type: "task_poll", task_kind: kind },
      timeout: "30s",
    });
    check(res, { [`${kind} task poll status 200`]: (r) => r.status === 200 });

    if (res.status !== 200) {
      sleep(pollSeconds);
      continue;
    }

    let task;
    try {
      task = res.json();
    } catch (e) {
      sleep(pollSeconds);
      continue;
    }

    if (task.status === "success") {
      const duration = Date.now() - startedAt;
      if (kind === "extract") {
        extractTaskDuration.add(duration);
        extractTaskSuccess.add(true);
      } else {
        transcribeTaskDuration.add(duration);
        transcribeTaskSuccess.add(true);
      }
      return true;
    }

    if (task.status === "failed") {
      console.error(`${kind.toUpperCase()} TASK FAILED id=${taskId} error=${String(task.error || "").slice(0, 500)}`);
      if (kind === "extract") {
        extractTaskSuccess.add(false);
      } else {
        transcribeTaskSuccess.add(false);
      }
      return false;
    }

    sleep(pollSeconds);
  }

  console.error(`${kind.toUpperCase()} TASK TIMEOUT id=${taskId}`);
  if (kind === "extract") {
    extractTaskSuccess.add(false);
  } else {
    transcribeTaskSuccess.add(false);
  }
  return false;
}

export const options = {
  scenarios: {
    normal_users: {
      executor: "constant-vus",
      vus: 6,
      duration: "10m",
      exec: "normalUser",
    },
    extract_users: {
      executor: "constant-vus",
      vus: 1,
      duration: "10m",
      exec: "extractUser",
      startTime: "10s",
    },
    transcribe_users: {
      executor: "constant-vus",
      vus: 1,
      duration: "10m",
      exec: "transcribeUser",
      startTime: "20s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    "http_req_duration{type:login}": ["p(95)<2000"],
    "http_req_duration{type:normal}": ["p(95)<2000"],
    "http_req_duration{type:extract_submit}": ["p(95)<1000"],
    "http_req_duration{type:transcribe_submit}": ["p(95)<3000"],
    "http_req_duration{type:task_poll}": ["p(95)<1000"],
    extract_task_success: ["rate>0.95"],
    transcribe_task_success: ["rate>0.95"],
  },
};

export function normalUser() {
  const token = login();
  if (!token) {
    sleep(randomIntBetween(2, 5));
    return;
  }
  sleep(randomIntBetween(1, 3));

  const listRes = http.get(`${BASE_URL}/api/results`, {
    headers: authHeaders(token),
    tags: { type: "normal" },
  });
  check(listRes, { "list status 200": (r) => r.status === 200 });
  sleep(randomIntBetween(2, 5));

  const transListRes = http.get(`${BASE_URL}/api/transcribe`, {
    headers: authHeaders(token),
    tags: { type: "normal" },
  });
  check(transListRes, { "transcribe list status 200": (r) => r.status === 200 });
  sleep(randomIntBetween(2, 5));

  http.get(`${BASE_URL}/api/auth/me`, {
    headers: authHeaders(token),
    tags: { type: "normal" },
  });
  sleep(randomIntBetween(2, 5));
}

export function extractUser() {
  const token = login();
  if (!token) {
    sleep(randomIntBetween(5, 10));
    return;
  }
  sleep(randomIntBetween(1, 2));

  const formData = {
    file: http.file(docFile, "sample.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
  };
  const res = http.post(`${BASE_URL}/api/extract`, formData, {
    headers: authHeaders(token),
    tags: { type: "extract_submit" },
    timeout: "60s",
  });
  check(res, {
    "extract submit status 200": (r) => r.status === 200,
    "extract submit has task_id": (r) => {
      try { return !!r.json().task_id; } catch (e) { return false; }
    },
  });
  if (res.status !== 200) {
    sleep(randomIntBetween(10, 20));
    return;
  }

  let taskId = "";
  try { taskId = res.json().task_id || ""; } catch (e) { }
  waitForTask(token, taskId, "extract");
  sleep(randomIntBetween(10, 20));
}

export function transcribeUser() {
  const token = login();
  if (!token) {
    sleep(randomIntBetween(5, 10));
    return;
  }
  sleep(randomIntBetween(1, 2));

  const formData = {
    file: http.file(audioFile, "sample.mp3", "audio/mpeg"),
  };
  const res = http.post(`${BASE_URL}/api/transcribe`, formData, {
    headers: authHeaders(token),
    tags: { type: "transcribe_submit" },
    timeout: "60s",
  });
  check(res, {
    "transcribe submit status 200": (r) => r.status === 200,
    "transcribe submit has task_id": (r) => {
      try { return !!r.json().task_id; } catch (e) { return false; }
    },
  });
  if (res.status !== 200) {
    sleep(randomIntBetween(10, 20));
    return;
  }

  let taskId = "";
  try { taskId = res.json().task_id || ""; } catch (e) { }
  waitForTask(token, taskId, "transcribe");
  sleep(randomIntBetween(10, 20));
}
