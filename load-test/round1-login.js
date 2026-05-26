// 第 1 轮：只测登录
// 目的：确认登录接口本身是否正常
// k6 run round1-login.js

import http from "k6/http";
import { check, sleep } from "k6";
import { randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8011";
const K6_USER = __ENV.K6_USER || "admin";
const K6_PASS = __ENV.K6_PASS || "admin123";

export const options = {
  scenarios: {
    login_only: {
      executor: "constant-vus",
      vus: 8,
      duration: "3m",
      exec: "loginOnly",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
  },
};

export function loginOnly() {
  const body = JSON.stringify({ username: K6_USER, password: K6_PASS });
  const res = http.post(`${BASE_URL}/api/auth/login`, body, {
    headers: { "Content-Type": "application/json" },
  });
  check(res, { "login status 200": (r) => r.status === 200 });
  sleep(randomIntBetween(1, 3));
}
