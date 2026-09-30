# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

## 1. Thông tin học viên

- **Họ và tên:** Trần Thị Thu Hiền
- **MSSV:** 2A202602737
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/hientran-ai/K4-L3B-Day13-Monitoring-LLMOps
- **Commit SHA cuối:** cập nhật sau khi commit evidence
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602737`

## 2. Evidence index

Ba output text dùng để kiểm tra tự động:

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | [pytest.txt](evidence/pytest.txt) |
| Log validator | [log-validator.txt](evidence/log-validator.txt) |
| Dashboard validator | [dashboard-validator.txt](evidence/dashboard-validator.txt) |

Bộ ảnh chi tiết 01–14:

| # | Nội dung | Đường dẫn |
|---:|---|---|
| 01 | Commit và pytest | [01-pytest.png](evidence/01-pytest.png) |
| 02 | Log validator | [02-log-validator.png](evidence/02-log-validator.png) |
| 03 | Dashboard validator | [03-dashboard-validator.png](evidence/03-dashboard-validator.png) |
| 04 | Structured log | [04-structured-log.png](evidence/04-structured-log.png) |
| 05 | PII redaction | [05-pii-redaction.png](evidence/05-pii-redaction.png) |
| 06 | Danh sách trace | [06-trace-list.png](evidence/06-trace-list.png) |
| 07 | Trace waterfall | [07-trace-waterfall.png](evidence/07-trace-waterfall.png) |
| 08a | Root trace metadata | [08a-trace-metadata.png](evidence/08a-trace-metadata.png) |
| 08b | Generation usage/cost | [08b-trace-metadata.png](evidence/08b-trace-metadata.png) |
| 09 | Prompt versions | [09-prompt-versions.png](evidence/09-prompt-versions.png) |
| 10a | Promote v2 | [10a-prompt-promote.png](evidence/10a-prompt-promote.png) |
| 10b | Rollback về v1 | [10b-prompt-rollback.png](evidence/10b-prompt-rollback.png) |
| 11 | Dashboard tổng quan | [11-dashboard-overview.png](evidence/11-dashboard-overview.png) |
| 12 | Incident metric | [12-incident-metric.png](evidence/12-incident-metric.png) |
| 13 | Incident log | [13-incident-log.png](evidence/13-incident-log.png) |
| 14 | Incident trace | [14-incident-trace.png](evidence/14-incident-trace.png) |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | Starter còn TODO, không lưu output baseline | 100/100 | Đủ schema, correlation, enrichment và PII scrubbing |
| `validate_dashboard.py` | Chưa có dashboard runtime hoàn chỉnh | 6/6 | Đủ sáu panel theo contract |
| `pytest` | Không lưu output baseline | 25 passed | Chạy toàn bộ test trên code cuối |
| Số traces hợp lệ | 0 trace cá nhân trước khi cấu hình | 23 root traces trong ảnh danh sách | Trace thuộc project cá nhân |
| Số PII leak | Chưa kiểm tra | 0 | Validator không phát hiện PII leak |
| Latency P95 / TTFT P95 | 1687 ms / 50 ms | Incident: 2654 ms / 50 ms | P95 vượt challenge threshold 2000 ms |
| Retrieval success rate | Chưa có dashboard | 100% | Incident là chậm, không phải retrieval failure |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** middleware nhận `x-request-id` hợp lệ theo dạng `req-<8-hex>`; nếu thiếu hoặc sai định dạng thì sinh ID mới. ID được bind vào context, lưu vào `request.state`, trả qua response header và truyền vào trace.
- **Các metadata được ghi vào structured log:** `ts`, `event`, `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, latency, TTFT, token, cost, quality và trạng thái retrieval.
- **Cách bảo đảm PII được scrub trước khi ghi:** processor đệ quy scrub mọi chuỗi trong event dictionary trước JSON renderer/file processor. Các rule che email, điện thoại Việt Nam, CCCD và thẻ thanh toán.
- **Cách kiểm chứng kết quả:** unit tests, log validator 100/100 và ảnh [05-pii-redaction.png](evidence/05-pii-redaction.png).

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo:** ảnh danh sách hiển thị project `day13-k4-l3b-2A202602737`, trace name `day13-agent-request`, environment `dev` và các request do workload của repo tạo.
- **Cấu trúc observations:** `lab-agent-run` là root/agent; `retrieval` và `generation` là hai observation con. Generation ghi model, token usage và cost.
- **Cách nối trace với log:** trường `correlation_id` xuất hiện trong structured log và trace metadata.
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** v1 có `baseline` và trạng thái cuối có `production`.
- **Version/label candidate:** v2 có `candidate`; đã được promote tạm thời rồi rollback.
- **Trace ID v1:** `df822194eae47d951f34554a6bdc3d1c`.
- **Trace ID v2:** `830f09ffe7651919b180d0134aef77b9`, observation version 2, correlation ID `req-2a202737`.
- **Cách promote và rollback:** chuyển label `production` sang v2 để chạy thử; sau đó gắn lại `production` cho v1 và giữ `candidate` ở v2.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** dashboard FastAPI đọc `data/logs.jsonl`, cửa sổ 60 phút, tự refresh 30 giây; gồm latency/TTFT, traffic, error/retrieval success, cost, token và quality.
- **SLO và lý do chọn:** trong cửa sổ 28 ngày, 99.5% request phải thành công và có latency không quá 3000 ms. Ngưỡng này bảo vệ trải nghiệm tail latency nhưng vẫn có dung sai vận hành.
- **Cách tính error budget:** target 99.5% tương ứng error budget 0.5%. Với 10,000 request, tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO.
- **Ba alert và runbook:** `HighLatencyP95`, `HighErrorRate`, `LowRetrievalSuccess` trong [config/alert_rules.yaml](../config/alert_rules.yaml), với hướng dẫn xử lý tại [docs/alerts.md](../docs/alerts.md).

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`.
- **Khoảng thời gian điều tra:** khoảng 12:22:22–12:22:36 ngày 30/09/2026 ICT (05:22 UTC), trong dashboard window 60 phút.
- **Triệu chứng từ metrics:** latency P95 tăng lên 2654 ms, vượt challenge threshold 2000 ms; TTFT P95 vẫn 50 ms và retrieval success vẫn 100%.
- **Log line và correlation ID:** event `response_sent`, `correlation_id=req-dc782ca5`, `latency_ms=2654`, `tool_name=retrieval`, timestamp `2026-09-30T05:22:36.689107Z`.
- **Trace ID và span gây ảnh hưởng:** trace `6962c44ee58a08ae37412548dc56e176`; root mất khoảng 2.65 giây, span `retrieval` khoảng 2.50 giây và generation khoảng 0.15 giây.
- **Root cause:** challenge bật scenario `rag_slow`, khiến retrieval thêm blocking delay 2.5 giây. Trace chứng minh phần lớn latency nằm ở retrieval, không nằm ở generation.
- **Fix action:** tắt `rag_slow`, khôi phục cấu hình retrieval bình thường và xác nhận lại P95 bằng cùng workload.
- **Preventive measure:** alert tail latency, theo dõi riêng retrieval duration/success, đặt timeout/fallback và chạy performance test trước khi triển khai thay đổi retrieval.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng:** không capture raw input/output vào trace; chỉ ghi preview đã scrub và metadata cần thiết để giảm nguy cơ rò rỉ PII.
- **Một lỗi/blocker đã gặp:** Windows App Control chặn DLL của `pandas`, nên dashboard dựa trên Streamlit không thể chạy ổn định trong môi trường máy học viên.
- **Cách tìm nguyên nhân và xử lý:** xác định lỗi nằm ở dependency native, sau đó triển khai dashboard HTML/SVG bằng FastAPI và thư viện chuẩn, vẫn dùng đúng `data/logs.jsonl` và sáu panel trong contract.
- **Cách hiểu luồng Metrics → Logs → Traces:** metrics xác định triệu chứng và thời gian; log chọn request đại diện bằng correlation ID; trace cùng ID cho biết span nào tiêu tốn thời gian; từ đó mới kết luận root cause.
- **Vai trò của prompt version, token/cost, SLO và rollback:** prompt version giúp truy vết cấu hình sinh câu trả lời; token/cost kiểm soát tài nguyên; SLO định nghĩa chất lượng chấp nhận được; label cho phép rollback nhanh mà không đổi source code.
- **Điều quan trọng nhất đã học:** không đoán nguyên nhân chỉ từ dashboard; cần chuỗi bằng chứng nhất quán từ metric đến log và trace.
- **Hạn chế còn lại:** dashboard dùng file JSONL cục bộ, phù hợp lab nhưng production cần metrics store, log backend, retention và alert delivery thật.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc repository cá nhân.
- [x] Tất cả ảnh/output dùng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân.
- [x] Repository chạy lại được theo README.
- [x] `.env`, secret, log runtime và môi trường ảo không được commit.
- [ ] Cập nhật commit SHA cuối sau commit evidence.
- [ ] Push commit cuối và nộp URL/SHA trên LMS/Codelabs.
