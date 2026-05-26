// 第 5 轮：真实 8 人混合场景
// 目的：复现真实故障 —— 重任务运行期间，普通用户是否还能正常操作
// 模拟: 6 个普通用户 + 1 个文档上传 + 1 个音频转写
// k6 run round5-mixed.js

import http from "k6/http";
import { check, sleep } from "k6";
import { randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8011";
const K6_USER = __ENV.K6_USER || "admin";
const K6_PASS = __ENV.K6_PASS || "admin123";

const docFile = open("./sample.docx", "b");
const audioFile = open("./sample.mp3", "b");

function login() {
  const body = JSON.stringify({ username: K6_USER, password: K6_PASS });
  const res = http.post(`${BASE_URL}/api/auth/login`, body, {
    headers: { "Content-Type": "application/json" },
  });
  check(res, { "login status 200": (r) => r.status === 200 });
  try { return res.json().token || ""; } catch (e) { return ""; }
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
  },
};

export function normalUser() {
  const token = login();
  sleep(randomIntBetween(1, 3));

  const listRes = http.get(`${BASE_URL}/api/results`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    tags: { type: "normal" },
  });
  check(listRes, { "list status 200": (r) => r.status === 200 });
  sleep(randomIntBetween(2, 5));

  const transListRes = http.get(`${BASE_URL}/api/transcribe`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    tags: { type: "normal" },
  });
  check(transListRes, { "transcribe list status 200": (r) => r.status === 200 });
  sleep(randomIntBetween(2, 5));

  http.get(`${BASE_URL}/api/auth/me`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    tags: { type: "normal" },
  });
  sleep(randomIntBetween(2, 5));
}

export function extractUser() {
  const token = login();
  sleep(randomIntBetween(1, 2));

  const formData = {
    file: http.file(docFile, "sample.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
  };
  const res = http.post(`${BASE_URL}/api/extract`, formData, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    tags: { type: "extract" },
    timeout: "600s",
  });
  check(res, { "extract status 200": (r) => r.status === 200 });
  sleep(randomIntBetween(3, 8));
}

export function transcribeUser() {
  const token = login();
  sleep(randomIntBetween(1, 2));

  const formData = {
    file: http.file(audioFile, "sample.mp3", "audio/mpeg"),
  };
  const res = http.post(`${BASE_URL}/api/transcribe`, formData, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    tags: { type: "transcribe" },
    timeout: "600s",
  });
  check(res, { "transcribe status 200": (r) => r.status === 200 });
  sleep(randomIntBetween(5, 10));
}
