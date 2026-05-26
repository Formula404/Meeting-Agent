// 第 2 轮：只测普通页面接口
// 目的：确认普通页面数据加载是否稳定
// k6 run round2-normal.js

import http from "k6/http";
import { check, sleep } from "k6";
import { randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8011";
const K6_USER = __ENV.K6_USER || "admin";
const K6_PASS = __ENV.K6_PASS || "admin123";

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
      vus: 8,
      duration: "5m",
      exec: "normalUser",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{type:normal}": ["p(95)<2000"],
  },
};

export function normalUser() {
  const token = login();
  sleep(randomIntBetween(1, 3));

  const endpoints = [
    "/api/results",
    "/api/transcribe",
    "/api/auth/me",
    "/api/users",
    "/api/departments",
  ];
  for (const ep of endpoints) {
    const res = http.get(`${BASE_URL}${ep}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      tags: { type: "normal" },
    });
    check(res, { [`${ep} status 200`]: (r) => r.status === 200 });
    sleep(randomIntBetween(1, 3));
  }
}
