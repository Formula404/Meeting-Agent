// 第 4 轮：只测音频转写
// 目的：判断 ASR 上传/轮询是否拖死后端
// 用法: k6 run round4-transcribe.js
//       VUS=2 k6 run round4-transcribe.js      (2 个转写用户)
//
// 建议:
//   VUS=1 → 单任务基线
//   VUS=2 → 看是否阻塞其他请求
//   VUS=4 → 谨慎，可能触发外部 ASR 限流/费用

import http from "k6/http";
import { check, sleep } from "k6";
import { randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8011";
const K6_USER = __ENV.K6_USER || "admin";
const K6_PASS = __ENV.K6_PASS || "admin123";
const VUS = parseInt(__ENV.VUS) || 1;

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
    transcribe_users: {
      executor: "constant-vus",
      vus: VUS,
      duration: __ENV.DURATION || "5m",
      exec: "transcribeUser",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
  },
};

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
