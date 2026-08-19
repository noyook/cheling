# 获取电子运单系统（图片验证码）数据
```
curl 'https://183.95.190.189:8681/inter/blade-auth/oauth/captcha' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --insecure
```

# 登录系统，获取token
```
curl 'https://183.95.190.189:8681/inter/blade-auth/oauth/token?tenantId=000000&username=13971673595&password=4qraWx9LwMK2tzeiDTFSEBoiaJUQEYs9pkEWvnd1Mfd%2BJ9QVM%2FyYVZsfdutU731y&grant_type=captcha&scope=all&type=account' \
  -X 'POST' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Cache-Control: no-cache' \
  -H 'Captcha-Code: 59446' \
  -H 'Captcha-Key: 0144d19a753319fbb4b570161e8472cd' \
  -H 'Connection: keep-alive' \
  -H 'Content-Length: 0' \
  -H 'Dept-Id;' \
  -H 'Origin: https://183.95.190.189:8681' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Role-Id;' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'Tenant-Id: 000000' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  -H 'systemType: qy-pc' \
  -H 'terminal: pc' \
  --insecure
```

# 获取 运单数据
```
curl 'https://183.95.190.189:8681/inter/qy-server/busibill/page?current=1&size=10&consignName=&vehCode=&rangeDate=2026-04-29,2026-05-06&billState=10,11,20,30,40,50,60,0&billNo=&driverEscortId=&pdfState=&startDate=2026-04-29&endDate=2026-05-06&flag=&approvalState=' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Blade-Auth: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI1NjA2MzMiLCJ6aXBDb2RlIjoiNDIwMTAwIiwiZW1wVHlwZSI6IjEiLCJ1c2VyX25hbWUiOiIxMzk3MTY3MzU5NSIsInR5cGVMZXZlbCI6LTEsInJlYWxfbmFtZSI6IuaWueaTjSIsIm93bmVySWQiOiIwMDAwMDAwMDczMWExZDU1MDE3MzMxNTQ2MjQwMDI0NCIsImNsaWVudF9pZCI6ImRncy13ZWIiLCJjcmVkaXRDb2RlIjoiOTE0MjAxMDM3NDQ3ODE2NTVNIiwib3duZXJOYW1lIjoi5q2m5rGJ6L-Q6YCa54eD5paZ5rG96L2m6L-Q6L6T5pyJ6ZmQ5YWs5Y-4Iiwicm9sZV9pZCI6IjE4ODkxMjIzMDg5NzMzMzA0MzQiLCJzY29wZSI6WyJhbGwiXSwib2F1dGhfaWQiOiIiLCJtY2VydFdvcmQiOiLmrabmsYkiLCJleHAiOjE3NzgxMTM5NTQsImp0aSI6IjNlZmQ0NTE4LTQ5NmItNDEyMi1iOGYyLWRlZDUyNDcxOGRjZSIsImF2YXRhciI6IiIsInVzZXJSb2xlVHlwZSI6MiwiYXV0aG9yaXRpZXMiOlsicXlfYWRtaW4iXSwicm9sZV9uYW1lIjoicXlfYWRtaW4iLCJwb3N0X2lkIjoiIiwidXNlcl9pZCI6IjE4OTcxNjc5MzA3NzA5OTMxNTMiLCJwaG9uZSI6IjEzOTcxNjczNTk1Iiwibmlja19uYW1lIjoi5pa55pONIiwibWNlcnRJZCI6IjQyMDExODEwMDA0MyIsIm90cF9hY3Rpb24iOjAsImVtcEluZm9JZCI6IjUzYjgzOGVlLTFhMGQtNGNmOC04ZGNiLWZiMDBiNzQyOTM2MiIsInBhc3N3ZEV4cCI6ZmFsc2UsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sInVzZXJUeXBlIjoiMiIsImRlcHRfaWQiOiIxODg5MTIyMzEwMDA1MTI5MjE4IiwiaXNaZmdoIjowLCJhY2NvdW50IjoiMTM5NzE2NzM1OTUiLCJlbXBJZENhcmQiOiI0MjAxMTQxOTgyMDMxNzAwNVgifQ.DX94IRoWi9PALYcMRx3TuuQSh_QqXyL7F_94YdinQmk' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --insecure
```

---

# 安全检查
```
curl 'https://183.95.190.189:8681/inter/qy-server/busidispcheck/page?vehCode=&updateUser=&taskState=3&taskId=&current=1&size=10&createTimeStart=2026-04-29&createTimeEnd=2026-05-06' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Blade-Auth: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI1NjA2MzMiLCJ6aXBDb2RlIjoiNDIwMTAwIiwiZW1wVHlwZSI6IjEiLCJ1c2VyX25hbWUiOiIxMzk3MTY3MzU5NSIsInR5cGVMZXZlbCI6LTEsInJlYWxfbmFtZSI6IuaWueaTjSIsIm93bmVySWQiOiIwMDAwMDAwMDczMWExZDU1MDE3MzMxNTQ2MjQwMDI0NCIsImNsaWVudF9pZCI6ImRncy13ZWIiLCJjcmVkaXRDb2RlIjoiOTE0MjAxMDM3NDQ3ODE2NTVNIiwib3duZXJOYW1lIjoi5q2m5rGJ6L-Q6YCa54eD5paZ5rG96L2m6L-Q6L6T5pyJ6ZmQ5YWs5Y-4Iiwicm9sZV9pZCI6IjE4ODkxMjIzMDg5NzMzMzA0MzQiLCJzY29wZSI6WyJhbGwiXSwib2F1dGhfaWQiOiIiLCJtY2VydFdvcmQiOiLmrabmsYkiLCJleHAiOjE3NzgxMTc3MDQsImp0aSI6IjRmMDUwYzQyLTRlZjItNDYwYy05Y2M4LWYyNDhhNTlkM2E0NiIsImF2YXRhciI6IiIsInVzZXJSb2xlVHlwZSI6MiwiYXV0aG9yaXRpZXMiOlsicXlfYWRtaW4iXSwicm9sZV9uYW1lIjoicXlfYWRtaW4iLCJwb3N0X2lkIjoiIiwidXNlcl9pZCI6IjE4OTcxNjc5MzA3NzA5OTMxNTMiLCJwaG9uZSI6IjEzOTcxNjczNTk1Iiwibmlja19uYW1lIjoi5pa55pONIiwibWNlcnRJZCI6IjQyMDExODEwMDA0MyIsIm90cF9hY3Rpb24iOjAsImVtcEluZm9JZCI6IjUzYjgzOGVlLTFhMGQtNGNmOC04ZGNiLWZiMDBiNzQyOTM2MiIsInBhc3N3ZEV4cCI6ZmFsc2UsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sInVzZXJUeXBlIjoiMiIsImRlcHRfaWQiOiIxODg5MTIyMzEwMDA1MTI5MjE4IiwiaXNaZmdoIjowLCJhY2NvdW50IjoiMTM5NzE2NzM1OTUiLCJlbXBJZENhcmQiOiI0MjAxMTQxOTgyMDMxNzAwNVgifQ.n_7dGN5fktHulGs8AE_E3wmta3MlIk_SSLiCkREz-vk' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --insecure
```

---

# 待审批运单
```
curl 'https://183.95.190.189:8681/inter/qy-server/busitask/detail?taskId=ce49db385bb7542cd5b0894499158ab6&id=2051839487355801601&dispCheckId=eda1219e87e9c3273acb83dda9de9e37&vehId=b4e1fb51-a23e-44c7-845b-7c2e9431f620' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Blade-Auth: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI1NjA2MzMiLCJ6aXBDb2RlIjoiNDIwMTAwIiwiZW1wVHlwZSI6IjEiLCJ1c2VyX25hbWUiOiIxMzk3MTY3MzU5NSIsInR5cGVMZXZlbCI6LTEsInJlYWxfbmFtZSI6IuaWueaTjSIsIm93bmVySWQiOiIwMDAwMDAwMDczMWExZDU1MDE3MzMxNTQ2MjQwMDI0NCIsImNsaWVudF9pZCI6ImRncy13ZWIiLCJjcmVkaXRDb2RlIjoiOTE0MjAxMDM3NDQ3ODE2NTVNIiwib3duZXJOYW1lIjoi5q2m5rGJ6L-Q6YCa54eD5paZ5rG96L2m6L-Q6L6T5pyJ6ZmQ5YWs5Y-4Iiwicm9sZV9pZCI6IjE4ODkxMjIzMDg5NzMzMzA0MzQiLCJzY29wZSI6WyJhbGwiXSwib2F1dGhfaWQiOiIiLCJtY2VydFdvcmQiOiLmrabmsYkiLCJleHAiOjE3NzgxMTc3MDQsImp0aSI6IjRmMDUwYzQyLTRlZjItNDYwYy05Y2M4LWYyNDhhNTlkM2E0NiIsImF2YXRhciI6IiIsInVzZXJSb2xlVHlwZSI6MiwiYXV0aG9yaXRpZXMiOlsicXlfYWRtaW4iXSwicm9sZV9uYW1lIjoicXlfYWRtaW4iLCJwb3N0X2lkIjoiIiwidXNlcl9pZCI6IjE4OTcxNjc5MzA3NzA5OTMxNTMiLCJwaG9uZSI6IjEzOTcxNjczNTk1Iiwibmlja19uYW1lIjoi5pa55pONIiwibWNlcnRJZCI6IjQyMDExODEwMDA0MyIsIm90cF9hY3Rpb24iOjAsImVtcEluZm9JZCI6IjUzYjgzOGVlLTFhMGQtNGNmOC04ZGNiLWZiMDBiNzQyOTM2MiIsInBhc3N3ZEV4cCI6ZmFsc2UsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sInVzZXJUeXBlIjoiMiIsImRlcHRfaWQiOiIxODg5MTIyMzEwMDA1MTI5MjE4IiwiaXNaZmdoIjowLCJhY2NvdW50IjoiMTM5NzE2NzM1OTUiLCJlbXBJZENhcmQiOiI0MjAxMTQxOTgyMDMxNzAwNVgifQ.n_7dGN5fktHulGs8AE_E3wmta3MlIk_SSLiCkREz-vk' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --insecure
```

```
curl 'https://183.95.190.189:8681/inter/qy-server/busidispcheck/selfCheckV2' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Blade-Auth: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI1NjA2MzMiLCJ6aXBDb2RlIjoiNDIwMTAwIiwiZW1wVHlwZSI6IjEiLCJ1c2VyX25hbWUiOiIxMzk3MTY3MzU5NSIsInR5cGVMZXZlbCI6LTEsInJlYWxfbmFtZSI6IuaWueaTjSIsIm93bmVySWQiOiIwMDAwMDAwMDczMWExZDU1MDE3MzMxNTQ2MjQwMDI0NCIsImNsaWVudF9pZCI6ImRncy13ZWIiLCJjcmVkaXRDb2RlIjoiOTE0MjAxMDM3NDQ3ODE2NTVNIiwib3duZXJOYW1lIjoi5q2m5rGJ6L-Q6YCa54eD5paZ5rG96L2m6L-Q6L6T5pyJ6ZmQ5YWs5Y-4Iiwicm9sZV9pZCI6IjE4ODkxMjIzMDg5NzMzMzA0MzQiLCJzY29wZSI6WyJhbGwiXSwib2F1dGhfaWQiOiIiLCJtY2VydFdvcmQiOiLmrabmsYkiLCJleHAiOjE3NzgxMTc3MDQsImp0aSI6IjRmMDUwYzQyLTRlZjItNDYwYy05Y2M4LWYyNDhhNTlkM2E0NiIsImF2YXRhciI6IiIsInVzZXJSb2xlVHlwZSI6MiwiYXV0aG9yaXRpZXMiOlsicXlfYWRtaW4iXSwicm9sZV9uYW1lIjoicXlfYWRtaW4iLCJwb3N0X2lkIjoiIiwidXNlcl9pZCI6IjE4OTcxNjc5MzA3NzA5OTMxNTMiLCJwaG9uZSI6IjEzOTcxNjczNTk1Iiwibmlja19uYW1lIjoi5pa55pONIiwibWNlcnRJZCI6IjQyMDExODEwMDA0MyIsIm90cF9hY3Rpb24iOjAsImVtcEluZm9JZCI6IjUzYjgzOGVlLTFhMGQtNGNmOC04ZGNiLWZiMDBiNzQyOTM2MiIsInBhc3N3ZEV4cCI6ZmFsc2UsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sInVzZXJUeXBlIjoiMiIsImRlcHRfaWQiOiIxODg5MTIyMzEwMDA1MTI5MjE4IiwiaXNaZmdoIjowLCJhY2NvdW50IjoiMTM5NzE2NzM1OTUiLCJlbXBJZENhcmQiOiI0MjAxMTQxOTgyMDMxNzAwNVgifQ.n_7dGN5fktHulGs8AE_E3wmta3MlIk_SSLiCkREz-vk' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -H 'Origin: https://183.95.190.189:8681' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --data-raw '{"dispCheckId":"eda1219e87e9c3273acb83dda9de9e37","taskId":"ce49db385bb7542cd5b0894499158ab6"}' \
  --insecure
```

```
curl 'https://183.95.190.189:8681/inter/blade-system/dict/list?code=safe_check_type' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Blade-Auth: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI1NjA2MzMiLCJ6aXBDb2RlIjoiNDIwMTAwIiwiZW1wVHlwZSI6IjEiLCJ1c2VyX25hbWUiOiIxMzk3MTY3MzU5NSIsInR5cGVMZXZlbCI6LTEsInJlYWxfbmFtZSI6IuaWueaTjSIsIm93bmVySWQiOiIwMDAwMDAwMDczMWExZDU1MDE3MzMxNTQ2MjQwMDI0NCIsImNsaWVudF9pZCI6ImRncy13ZWIiLCJjcmVkaXRDb2RlIjoiOTE0MjAxMDM3NDQ3ODE2NTVNIiwib3duZXJOYW1lIjoi5q2m5rGJ6L-Q6YCa54eD5paZ5rG96L2m6L-Q6L6T5pyJ6ZmQ5YWs5Y-4Iiwicm9sZV9pZCI6IjE4ODkxMjIzMDg5NzMzMzA0MzQiLCJzY29wZSI6WyJhbGwiXSwib2F1dGhfaWQiOiIiLCJtY2VydFdvcmQiOiLmrabmsYkiLCJleHAiOjE3NzgxMTc3MDQsImp0aSI6IjRmMDUwYzQyLTRlZjItNDYwYy05Y2M4LWYyNDhhNTlkM2E0NiIsImF2YXRhciI6IiIsInVzZXJSb2xlVHlwZSI6MiwiYXV0aG9yaXRpZXMiOlsicXlfYWRtaW4iXSwicm9sZV9uYW1lIjoicXlfYWRtaW4iLCJwb3N0X2lkIjoiIiwidXNlcl9pZCI6IjE4OTcxNjc5MzA3NzA5OTMxNTMiLCJwaG9uZSI6IjEzOTcxNjczNTk1Iiwibmlja19uYW1lIjoi5pa55pONIiwibWNlcnRJZCI6IjQyMDExODEwMDA0MyIsIm90cF9hY3Rpb24iOjAsImVtcEluZm9JZCI6IjUzYjgzOGVlLTFhMGQtNGNmOC04ZGNiLWZiMDBiNzQyOTM2MiIsInBhc3N3ZEV4cCI6ZmFsc2UsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sInVzZXJUeXBlIjoiMiIsImRlcHRfaWQiOiIxODg5MTIyMzEwMDA1MTI5MjE4IiwiaXNaZmdoIjowLCJhY2NvdW50IjoiMTM5NzE2NzM1OTUiLCJlbXBJZENhcmQiOiI0MjAxMTQxOTgyMDMxNzAwNVgifQ.n_7dGN5fktHulGs8AE_E3wmta3MlIk_SSLiCkREz-vk' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --insecure
```

```
curl 'https://183.95.190.189:8681/inter/qy-server/busidispcheck/detail?dispCheckId=eda1219e87e9c3273acb83dda9de9e37' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Blade-Auth: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI1NjA2MzMiLCJ6aXBDb2RlIjoiNDIwMTAwIiwiZW1wVHlwZSI6IjEiLCJ1c2VyX25hbWUiOiIxMzk3MTY3MzU5NSIsInR5cGVMZXZlbCI6LTEsInJlYWxfbmFtZSI6IuaWueaTjSIsIm93bmVySWQiOiIwMDAwMDAwMDczMWExZDU1MDE3MzMxNTQ2MjQwMDI0NCIsImNsaWVudF9pZCI6ImRncy13ZWIiLCJjcmVkaXRDb2RlIjoiOTE0MjAxMDM3NDQ3ODE2NTVNIiwib3duZXJOYW1lIjoi5q2m5rGJ6L-Q6YCa54eD5paZ5rG96L2m6L-Q6L6T5pyJ6ZmQ5YWs5Y-4Iiwicm9sZV9pZCI6IjE4ODkxMjIzMDg5NzMzMzA0MzQiLCJzY29wZSI6WyJhbGwiXSwib2F1dGhfaWQiOiIiLCJtY2VydFdvcmQiOiLmrabmsYkiLCJleHAiOjE3NzgxMTc3MDQsImp0aSI6IjRmMDUwYzQyLTRlZjItNDYwYy05Y2M4LWYyNDhhNTlkM2E0NiIsImF2YXRhciI6IiIsInVzZXJSb2xlVHlwZSI6MiwiYXV0aG9yaXRpZXMiOlsicXlfYWRtaW4iXSwicm9sZV9uYW1lIjoicXlfYWRtaW4iLCJwb3N0X2lkIjoiIiwidXNlcl9pZCI6IjE4OTcxNjc5MzA3NzA5OTMxNTMiLCJwaG9uZSI6IjEzOTcxNjczNTk1Iiwibmlja19uYW1lIjoi5pa55pONIiwibWNlcnRJZCI6IjQyMDExODEwMDA0MyIsIm90cF9hY3Rpb24iOjAsImVtcEluZm9JZCI6IjUzYjgzOGVlLTFhMGQtNGNmOC04ZGNiLWZiMDBiNzQyOTM2MiIsInBhc3N3ZEV4cCI6ZmFsc2UsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sInVzZXJUeXBlIjoiMiIsImRlcHRfaWQiOiIxODg5MTIyMzEwMDA1MTI5MjE4IiwiaXNaZmdoIjowLCJhY2NvdW50IjoiMTM5NzE2NzM1OTUiLCJlbXBJZENhcmQiOiI0MjAxMTQxOTgyMDMxNzAwNVgifQ.n_7dGN5fktHulGs8AE_E3wmta3MlIk_SSLiCkREz-vk' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --insecure
```

```
curl 'https://183.95.190.189:8681/inter/qy-server/mgntvehrunlog/detail?taskId=ce49db385bb7542cd5b0894499158ab6&logType=10' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Blade-Auth: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI1NjA2MzMiLCJ6aXBDb2RlIjoiNDIwMTAwIiwiZW1wVHlwZSI6IjEiLCJ1c2VyX25hbWUiOiIxMzk3MTY3MzU5NSIsInR5cGVMZXZlbCI6LTEsInJlYWxfbmFtZSI6IuaWueaTjSIsIm93bmVySWQiOiIwMDAwMDAwMDczMWExZDU1MDE3MzMxNTQ2MjQwMDI0NCIsImNsaWVudF9pZCI6ImRncy13ZWIiLCJjcmVkaXRDb2RlIjoiOTE0MjAxMDM3NDQ3ODE2NTVNIiwib3duZXJOYW1lIjoi5q2m5rGJ6L-Q6YCa54eD5paZ5rG96L2m6L-Q6L6T5pyJ6ZmQ5YWs5Y-4Iiwicm9sZV9pZCI6IjE4ODkxMjIzMDg5NzMzMzA0MzQiLCJzY29wZSI6WyJhbGwiXSwib2F1dGhfaWQiOiIiLCJtY2VydFdvcmQiOiLmrabmsYkiLCJleHAiOjE3NzgxMTc3MDQsImp0aSI6IjRmMDUwYzQyLTRlZjItNDYwYy05Y2M4LWYyNDhhNTlkM2E0NiIsImF2YXRhciI6IiIsInVzZXJSb2xlVHlwZSI6MiwiYXV0aG9yaXRpZXMiOlsicXlfYWRtaW4iXSwicm9sZV9uYW1lIjoicXlfYWRtaW4iLCJwb3N0X2lkIjoiIiwidXNlcl9pZCI6IjE4OTcxNjc5MzA3NzA5OTMxNTMiLCJwaG9uZSI6IjEzOTcxNjczNTk1Iiwibmlja19uYW1lIjoi5pa55pONIiwibWNlcnRJZCI6IjQyMDExODEwMDA0MyIsIm90cF9hY3Rpb24iOjAsImVtcEluZm9JZCI6IjUzYjgzOGVlLTFhMGQtNGNmOC04ZGNiLWZiMDBiNzQyOTM2MiIsInBhc3N3ZEV4cCI6ZmFsc2UsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sInVzZXJUeXBlIjoiMiIsImRlcHRfaWQiOiIxODg5MTIyMzEwMDA1MTI5MjE4IiwiaXNaZmdoIjowLCJhY2NvdW50IjoiMTM5NzE2NzM1OTUiLCJlbXBJZENhcmQiOiI0MjAxMTQxOTgyMDMxNzAwNVgifQ.n_7dGN5fktHulGs8AE_E3wmta3MlIk_SSLiCkREz-vk' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --insecure
```

```
curl 'https://183.95.190.189:8681/inter/qy-server/mgntvehrunlog/detail?taskId=ce49db385bb7542cd5b0894499158ab6&logType=10' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Blade-Auth: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI1NjA2MzMiLCJ6aXBDb2RlIjoiNDIwMTAwIiwiZW1wVHlwZSI6IjEiLCJ1c2VyX25hbWUiOiIxMzk3MTY3MzU5NSIsInR5cGVMZXZlbCI6LTEsInJlYWxfbmFtZSI6IuaWueaTjSIsIm93bmVySWQiOiIwMDAwMDAwMDczMWExZDU1MDE3MzMxNTQ2MjQwMDI0NCIsImNsaWVudF9pZCI6ImRncy13ZWIiLCJjcmVkaXRDb2RlIjoiOTE0MjAxMDM3NDQ3ODE2NTVNIiwib3duZXJOYW1lIjoi5q2m5rGJ6L-Q6YCa54eD5paZ5rG96L2m6L-Q6L6T5pyJ6ZmQ5YWs5Y-4Iiwicm9sZV9pZCI6IjE4ODkxMjIzMDg5NzMzMzA0MzQiLCJzY29wZSI6WyJhbGwiXSwib2F1dGhfaWQiOiIiLCJtY2VydFdvcmQiOiLmrabmsYkiLCJleHAiOjE3NzgxMTc3MDQsImp0aSI6IjRmMDUwYzQyLTRlZjItNDYwYy05Y2M4LWYyNDhhNTlkM2E0NiIsImF2YXRhciI6IiIsInVzZXJSb2xlVHlwZSI6MiwiYXV0aG9yaXRpZXMiOlsicXlfYWRtaW4iXSwicm9sZV9uYW1lIjoicXlfYWRtaW4iLCJwb3N0X2lkIjoiIiwidXNlcl9pZCI6IjE4OTcxNjc5MzA3NzA5OTMxNTMiLCJwaG9uZSI6IjEzOTcxNjczNTk1Iiwibmlja19uYW1lIjoi5pa55pONIiwibWNlcnRJZCI6IjQyMDExODEwMDA0MyIsIm90cF9hY3Rpb24iOjAsImVtcEluZm9JZCI6IjUzYjgzOGVlLTFhMGQtNGNmOC04ZGNiLWZiMDBiNzQyOTM2MiIsInBhc3N3ZEV4cCI6ZmFsc2UsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sInVzZXJUeXBlIjoiMiIsImRlcHRfaWQiOiIxODg5MTIyMzEwMDA1MTI5MjE4IiwiaXNaZmdoIjowLCJhY2NvdW50IjoiMTM5NzE2NzM1OTUiLCJlbXBJZENhcmQiOiI0MjAxMTQxOTgyMDMxNzAwNVgifQ.n_7dGN5fktHulGs8AE_E3wmta3MlIk_SSLiCkREz-vk' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --insecure
```

## 运单审批
```
curl 'https://183.95.190.189:8681/inter/qy-server/busidispcheck/check' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en,zh-CN;q=0.9,zh;q=0.8' \
  -H 'Authorization: Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==' \
  -H 'Blade-Auth: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI1NjA2MzMiLCJ6aXBDb2RlIjoiNDIwMTAwIiwiZW1wVHlwZSI6IjEiLCJ1c2VyX25hbWUiOiIxMzk3MTY3MzU5NSIsInR5cGVMZXZlbCI6LTEsInJlYWxfbmFtZSI6IuaWueaTjSIsIm93bmVySWQiOiIwMDAwMDAwMDczMWExZDU1MDE3MzMxNTQ2MjQwMDI0NCIsImNsaWVudF9pZCI6ImRncy13ZWIiLCJjcmVkaXRDb2RlIjoiOTE0MjAxMDM3NDQ3ODE2NTVNIiwib3duZXJOYW1lIjoi5q2m5rGJ6L-Q6YCa54eD5paZ5rG96L2m6L-Q6L6T5pyJ6ZmQ5YWs5Y-4Iiwicm9sZV9pZCI6IjE4ODkxMjIzMDg5NzMzMzA0MzQiLCJzY29wZSI6WyJhbGwiXSwib2F1dGhfaWQiOiIiLCJtY2VydFdvcmQiOiLmrabmsYkiLCJleHAiOjE3NzgxMTc3MDQsImp0aSI6IjRmMDUwYzQyLTRlZjItNDYwYy05Y2M4LWYyNDhhNTlkM2E0NiIsImF2YXRhciI6IiIsInVzZXJSb2xlVHlwZSI6MiwiYXV0aG9yaXRpZXMiOlsicXlfYWRtaW4iXSwicm9sZV9uYW1lIjoicXlfYWRtaW4iLCJwb3N0X2lkIjoiIiwidXNlcl9pZCI6IjE4OTcxNjc5MzA3NzA5OTMxNTMiLCJwaG9uZSI6IjEzOTcxNjczNTk1Iiwibmlja19uYW1lIjoi5pa55pONIiwibWNlcnRJZCI6IjQyMDExODEwMDA0MyIsIm90cF9hY3Rpb24iOjAsImVtcEluZm9JZCI6IjUzYjgzOGVlLTFhMGQtNGNmOC04ZGNiLWZiMDBiNzQyOTM2MiIsInBhc3N3ZEV4cCI6ZmFsc2UsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sInVzZXJUeXBlIjoiMiIsImRlcHRfaWQiOiIxODg5MTIyMzEwMDA1MTI5MjE4IiwiaXNaZmdoIjowLCJhY2NvdW50IjoiMTM5NzE2NzM1OTUiLCJlbXBJZENhcmQiOiI0MjAxMTQxOTgyMDMxNzAwNVgifQ.n_7dGN5fktHulGs8AE_E3wmta3MlIk_SSLiCkREz-vk' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -H 'Origin: https://183.95.190.189:8681' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://183.95.190.189:8681/dgsqy/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --data-raw '{"checkNote":"","checkState":"1","dispCheckId":"eda1219e87e9c3273acb83dda9de9e37","taskId":"ce49db385bb7542cd5b0894499158ab6","peoCheckdicts":[{"id":"1893826703426473985","dictId":"6f0c552846583c5aa1e13772aad87213","ownerId":"00000000731a1d550173315462400244","checkType":"50","checkPro":"车辆与人员资质检查、运输任务合法性检查、车辆技术状况检查；","checkContent":"1. 确认车辆的危险货物运输许可证、车辆技术等级评定是否在有效期内，车辆是否具备运输相应危险品的资质。\n2. 核实驾驶员、押运员的从业资格证是否合法、有效，是否熟悉岗位职责、安全操作规程和应急处置等内容。\n3. 检查运输任务是否符合企业的经营范围，是否与电子运单填写内容一致。\n4. 查看车辆近12个月内的维护记录，确认维护频次是否符合要求，车辆技术档案是否完整。\n5. 检查车辆、罐式车辆罐体、可移动罐柜、罐箱及相关设备技术状况及卫星定位装置检查记录。","sortNum":1,"note":"","createUser":1889122310109945900,"createTime":"2025-02-24 08:54:06","updateUser":0,"updateTime":null,"isDeleted":0}],"selfCheckData":{"mcert":true,"vehicleCcert":true,"vehicleGoods":true,"vehicleNextCheckDate":true,"vehicleInsuredValidDate":true,"vehicleRankDate":true,"tonnage":true,"driverEcertTime":true,"escortEcertTime":true,"driverEcertMatch":true,"escortEcertMatch":true,"gps":true,"ownerCert":"1","vehCert":"1","vehGoods":"1","annualReview":"1","insuredValid":"1","vehTecRank":"1","overload":"1","driverLic":"1","escortLic":"1","driverQualifica":"1","escorQualifica":"1","gpsterminal":"1"}}' \
  --insecure
```


