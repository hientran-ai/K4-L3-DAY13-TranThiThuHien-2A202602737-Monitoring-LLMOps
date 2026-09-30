# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của các event `response_sent`; SLO chính yêu cầu request tốt có latency không quá 3000 ms.
- Điều kiện và thời gian duy trì: `p95(response_sent.latency_ms) > 3000` liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn để nhận câu trả lời, đặc biệt ở nhóm request chậm nhất.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel latency, xác nhận P95/P99, TTFT và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, chọn một `response_sent` có `latency_ms` cao và lấy `correlation_id`.
  3. Mở trace có cùng `correlation_id` trên Langfuse, so sánh duration của retrieval và generation.
- Mitigation tạm thời: rollback prompt `production` nếu regression trùng với lần promote; nếu retrieval chậm thì tắt practice incident hoặc khôi phục cấu hình retrieval gần nhất.
- Owner: `student-<MSSV>`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: tỷ lệ request thất bại; guardrail yêu cầu error rate không quá 2%.
- Điều kiện và thời gian duy trì: `count(request_failed) / count(request_received) * 100 > 2` liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: request trả HTTP 500 và người dùng không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel errors để xác nhận error rate và nhóm `error_type` đang tăng.
  2. Lọc event `request_failed`, lấy `correlation_id`, `error_type`, `tool_name` và `tool_success` của một request đại diện.
  3. Mở trace cùng `correlation_id`, kiểm tra observation lỗi và status của retrieval/generation.
- Mitigation tạm thời: tắt incident/config gây lỗi, rollback thay đổi gần nhất và chuyển sang prompt/config ổn định trong khi điều tra.
- Owner: `student-<MSSV>`

## Alert 3

- Tên: `LowRetrievalSuccess`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: retrieval success rate; guardrail yêu cầu ít nhất 90%.
- Điều kiện và thời gian duy trì: `count(tool_success == true) / count(tool_success != null) * 100 < 90` liên tục trong 10 phút.
- Ảnh hưởng tới người dùng: agent thiếu context phù hợp, có thể trả lời sai, thiếu căn cứ hoặc thất bại hoàn toàn.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel errors/retrieval để xác nhận success rate và khoảng thời gian suy giảm.
  2. Lọc log có `tool_name=retrieval` và `tool_success=false`, sau đó lấy một `correlation_id` đại diện.
  3. Mở trace tương ứng, kiểm tra input preview an toàn, status retrieval và số document trả về.
- Mitigation tạm thời: khôi phục cấu hình/index retrieval ổn định, tắt incident practice và dùng fallback an toàn nếu hệ thống hỗ trợ.
- Owner: `student-<MSSV>`
