// k6 压力测试脚本 —— Meeting Agent
// 使用: k6 run test.js
// 环境变量:
//   BASE_URL  - 服务地址 (默认 http://127.0.0.1:8011)
//   K6_USER   - 登录用户名 (默认 admin)     ⚠️ 不要用 USERNAME，Windows 会冲突出错
//   K6_PASS   - 登录密码 (默认 admin123)
//   SCENARIO  - 测试场景 (login|normal|extract|transcribe|mixed, 默认 mixed)
//   VUS       - 并发数 (默认看场景)

import http from "k6/http";
import { check, sleep } from "k6";
import { randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8011";
const K6_USER = __ENV.K6_USER || "admin";
const K6_PASS = __ENV.K6_PASS || "admin123";
const SCENARIO = __ENV.SCENARIO || "mixed";

// 测试文件 —— 在 load-test/ 目录放置:
//   sample.docx  (小文档, ~100KB)
//   sample.mp3   (短音频, ~30秒)
const docFile = open("./sample.docx", "b");
const audioFile = open("./sample.mp3", "b");

// ─── 场景配置 ───────────────────────────────────────────────────────

function getScenarios() {
  switch (SCENARIO) {
    case "login":
      return {
        login_only: {
          executor: "constant-vus",
          vus: parseInt(__ENV.VUS) || 8,
          duration: "3m",
          exec: "loginOnly",
        },
      };
    case "normal":
      return {
        normal_users: {
          executor: "constant-vus",
          vus: parseInt(__ENV.VUS) || 8,
          duration: "5m",
          exec: "normalUser",
        },
      };
    case "extract":
      return {
        extract_users: {
          executor: "constant-vus",
          vus: parseInt(__ENV.VUS) || 2,
          duration: "5m",
          exec: "extractUser",
        },
      };
    case "transcribe":
      return {
        transcribe_users: {
          executor: "constant-vus",
          vus: parseInt(__ENV.VUS) || 1,
          duration: "5m",
          exec: "transcribeUser",
        },
      };
    case "mixed":
    default:
      return {
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
      };
  }
}

export const options = {
  scenarios: getScenarios(),
  thresholds: {
    http_req_failed: ["rate<0.05"],
    "http_req_duration{type:login}": ["p(95)<2000"],
    "http_req_duration{type:normal}": ["p(95)<2000"],
    "http_req_duration{type:extract}": ["p(95)<120000"],
    "http_req_duration{type:transcribe}": ["p(95)<600000"],
  },
};

// ─── 辅助函数 ───────────────────────────────────────────────────────

function login() {
  const body = JSON.stringify({ username: K6_USER, password: K6_PASS });
  const res = http.post(`${BASE_URL}/api/auth/login`, body, {
    headers: { "Content-Type": "application/json" },
  });
  check(res, { "login status 200": (r) => r.status === 200 });
  let token = "";
  try {
    token = res.json().token || "";
  } catch (e) {}
  return token;
}

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── 执行函数 ───────────────────────────────────────────────────────

export function loginOnly() {
  login();
  sleep(randomIntBetween(1, 3));
}

export function normalUser() {
  const token = login();
  sleep(randomIntBetween(1, 3));

  const listRes = http.get(`${BASE_URL}/api/results`, {
    headers: authHeaders(token), tags: { type: "normal" },
  });
  check(listRes, { "list status 200": (r) => r.status === 200 });
  sleep(randomIntBetween(2, 5));

  const transListRes = http.get(`${BASE_URL}/api/transcribe`, {
    headers: authHeaders(token), tags: { type: "normal" },
  });
  check(transListRes, { "transcribe list status 200": (r) => r.status === 200 });
  sleep(randomIntBetween(2, 5));

  http.get(`${BASE_URL}/api/auth/me`, {
    headers: authHeaders(token), tags: { type: "normal" },
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
    headers: { ...authHeaders(token) },
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
    headers: { ...authHeaders(token) },
    tags: { type: "transcribe" },
    timeout: "600s",
  });
  check(res, { "transcribe status 200": (r) => r.status === 200 });
  sleep(randomIntBetween(5, 10));
}
