// 第 3 轮：只测文档上传提取
// 目的：判断 LLM 提取任务的并发瓶颈
// 用法: k6 run round3-extract.js
//       VUS=4 k6 run round3-extract.js   (改并发数)
//
// 建议矩阵:
//   VUS=1, duration=3m   → 单任务基线
//   VUS=2, duration=5m   → 看是否线性变慢
//   VUS=4, duration=5m   → 看 workers/线程池是否排队
//   VUS=8, duration=5m   → 复现故障

import http from "k6/http";
import { check, sleep } from "k6";
import { randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8011";
const K6_USER = __ENV.K6_USER || "admin";
const K6_PASS = __ENV.K6_PASS || "admin123";
const VUS = parseInt(__ENV.VUS) || 2;

const docFile = open("./sample.docx", "b");

function login() {
  const body = JSON.stringify({ username: K6_USER, password: K6_PASS });
  const res = http.post(`${BASE_URL}/api/auth/login`, body, {
    headers: { "Content-Type": "application/json" },
  });
  check(res, { "login status 200": (r) => r.status === 200 });
  if (res.status !== 200) {
    console.error(
      `LOGIN FAILED status=${res.status} error=${res.error} body=${String(res.body).slice(0, 500)}`
    );
  }
  try { return res.json().token || ""; } catch (e) { return ""; }
}

export const options = {
  scenarios: {
    extract_users: {
      executor: "constant-vus",
      vus: VUS,
      duration: __ENV.DURATION || "5m",
      exec: "extractUser",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    "http_req_duration{type:extract}": ["p(95)<120000"],
  },
};

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
  if (res.status !== 200) {
    console.error(
      `EXTRACT FAILED status=${res.status} error=${res.error} body=${String(res.body).slice(0, 500)}`
    );
  }
  sleep(randomIntBetween(3, 8));
}
