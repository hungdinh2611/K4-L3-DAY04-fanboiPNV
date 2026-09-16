# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm: fanboi-PNV
- Người đại diện / MSSV: Dinh Bao Hung / 2A202602524
- Tên repo: `K4-L3-DAY04-DinhBaoHung-2A202602524-PromptEngineeringToolCalling` [CẦN ĐỔI LẠI TRÊN GITHUB — hiện repo đang tên `K4-L3-DAY04-fanboiPNV`, không đúng format đề yêu cầu]
- URL repo, nhánh nộp, commit chốt: https://github.com/hungdinh2611/K4-L3-DAY04-fanboiPNV 
- Deadline áp dụng và link thông báo đổi hạn nếu có: 12h trưa ngày 16/9/2026

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| Dinh Bao Hung | 2A202602524 | hungdinh2611 | Chạy kiểm thử v0, sửa prompt fix lỗi wrong_boundary (H12, M05, M09) và wrong_tool (H04, H13) | system_prompt.md — tạo branch v1, update system prompt v1 |
| Tran Anh Dang | 2A202602992 | B22DCCN211-TranAnhDang | Làm UI | Thiết kế UI/UX, update UI/UX |
| Nguyen Thanh Nam | 2A202602694 | namnt1204 | Sửa missing_info (case H10, H11, H19) | system_prompt.md — commit v2 |
| Nguyen Minh Quan | 2A202602490 | quan05102k4 | Làm test case | Tạo 10 test case (data/eval_group.json) |
| Hoang Anh Tu | 2A202602643 | ttien0181 | Sửa wrong_tool (case H17) | system_prompt.md |

## Nhận xét chung

Kết quả và bằng chứng:
v0 (baseline, suite base, 30 case): case_accuracy 0.70, tool_routing_accuracy 0.7667, argument_accuracy 0.70, multiturn_accuracy 0.80. Lỗi: wrong_tool 3, missing_info 3, wrong_boundary 3.
v1 (fix wrong_boundary — bắt buộc gọi tool clarify với response_type: yes_no trước mọi write action; xác nhận cũ hết hiệu lực khi payload đổi), suite base: case_accuracy 0.70 → 0.80, tool_routing_accuracy 0.7667 → 0.8667, argument_accuracy 0.70 → 0.80, multiturn_accuracy 0.80 → 1.00. wrong_boundary 3 → 0 (H12, M05, M09 PASS). wrong_tool và missing_info giữ nguyên 3.
v2 (fix wrong_tool — không gọi inspect_device bằng employee ID, set đúng check theo phần cụ thể được hỏi thay vì mặc định "all"), suite base: case_accuracy 0.80 → 0.9333, tool_routing_accuracy → 0.9333, argument_accuracy → 0.9333, multiturn_accuracy giữ 1.00. wrong_tool 3 → 0 (H04, H13, H17 PASS). missing_info giảm thêm ngoài dự kiến: 3 → 2 (H10 tự PASS dù không thuộc phạm vi v2).
v3 (fix missing_info — bắt buộc gọi clarify khi thiếu tham số bắt buộc hoặc mơ hồ giữa nhiều giá trị hợp lệ), suite base: case_accuracy 0.9333 → 0.9667, tool_routing_accuracy → 1.0, multiturn_accuracy giữ 1.00. missing_info 2 → 0 (H11, H19 PASS). Regression phát sinh: H03_kb_routing — case trước giờ luôn PASS ở v0-v2 — chuyển FAIL (wrong_tool/wrong_arg_value), không thuộc nhóm lỗi mà v3 nhắm tới.
v3, suite group (10 case tự viết — 5 một lượt + 5 nhiều lượt): case_accuracy 1.0, tool_routing_accuracy 1.0, argument_accuracy 1.0, multiturn_accuracy 1.0, 10/10 case PASS, không có failure nào. Bao gồm đủ các dạng: routing thiết bị/nhân viên/KB, trích đúng tham số check, hỏi lại khi thiếu employee_id ("của tôi"), giữ đúng asset/employee ID qua các lượt sửa, hủy yêu cầu tạo ticket giữa chừng, đổi ý định (status → KB), và giữ đúng boundary xác nhận khi priority đổi ở lượt sau.
Chạy adversarial (12 case, trên bản v3): case_accuracy 0.75 (9/12 PASS), tool_routing_accuracy 0.75, argument_accuracy 0.75, multiturn_accuracy 0.5. failure_counts: wrong_boundary 3. 3 case fail: A05_sensitive_ticket_payload, A11_multiturn_role_spoof, A12_external_identifier_smuggling — cùng loại wrong_boundary, cho thấy cơ chế xác nhận (rule đã fix ở v1) vẫn có thể bị lách qua các kỹ thuật tấn công tinh vi hơn (giả danh vai trò qua nhiều lượt hội thoại, chèn payload nhạy cảm vào ticket, mượn identifier từ nguồn bên ngoài thay vì từ chính người dùng).

## INDIVIDUAL

### Dinh Bao Hung — 2A202602524

- Phần việc và file/commit/PR: Chạy v0 baseline, viết và chạy v1 (fix wrong_boundary: H12, M05, M09) và v2 (fix wrong_tool: H04, H13). File: `starter_v0/artifacts/system_prompt.md` — branch v1.
- Quyết định, khó khăn và cách xử lý: Lần đầu viết rule xác nhận ("never perform a write action until confirmed") quá trừu tượng, chạy v1 không cải thiện gì (case_accuracy vẫn 0.70) vì agent tự gọi thẳng `create_ticket` với cờ `confirmed: false/true` thay vì gọi tool `clarify`. Đọc transcript thật mới phát hiện nguyên nhân, sửa lại rule để chỉ rõ tên tool `clarify` và điều kiện gọi — sau đó case_accuracy tăng lên 0.80 và multiturn_accuracy đạt 1.00.
- Điều đã học: Không nên viết rule ở mức nguyên tắc trừu tượng khi model có tool cụ thể để thực hiện hành vi đó — phải nói rõ tên tool và cơ chế, nếu không model sẽ tự "sáng tạo" cách tuân thủ theo cách sai. Đọc trace/tool result thật quan trọng hơn suy đoán từ tên lỗi.
- AI/công cụ đã dùng và cách kiểm tra: Claude — dùng để phân tích run JSON (transcript thật của từng case), chẩn đoán nguyên nhân lỗi, và đề xuất patch cho system_prompt.md. Kiểm tra bằng cách chạy lại `run_eval.py` sau mỗi lần sửa, so sánh case_accuracy và PASS/FAIL từng case trước-sau.
- Thời điểm đã tự nộp URL repo chung trên VLearn: 8:00 sáng 16/9/2026

### Tran Anh Dang — 2A202602992

- Phần việc và file/commit/PR: Thiết kế và cập nhật UI/UX.
- Quyết định, khó khăn và cách xử lý: Khó khăn chính là thiết kế giao diện phải hiển thị được cả tool call, input, kết quả/lỗi và version đang chạy cho từng lượt hội thoại, không chỉ hiện câu trả lời cuối cùng. Quyết định tách riêng khu vực log kỹ thuật (tool trace) khỏi khung chat chính để người xem dễ đối chiếu request với hành động thực tế của agent.
- Điều đã học: Một giao diện đẹp không đủ làm bằng chứng nếu không lộ ra lỗi tool — phải chủ động test bằng cách gây lỗi tool giả để xem UI có hiển thị đúng không, thay vì chỉ test trên luồng thành công.
- AI/công cụ đã dùng và cách kiểm tra: Claudecode hỗ trợ sinh UI theo prompt
- Thời điểm đã tự nộp URL repo chung trên VLearn: 20:55, 15/9/2026

### Nguyen Thanh Nam — 2A202602694

- Phần việc và file/commit/PR: Sửa `system_prompt.md` fix missing_info (H10, H11, H19) — commit v2.
- Quyết định, khó khăn và cách xử lý: Ở bản trước, agent tự đoán giá trị khi thiếu thông tin (vd tự gán asset_id="laptop" hoặc employee_id="Sales") thay vì hỏi lại. Quyết định thêm rule bắt buộc gọi tool clarify khi thiếu tham số bắt buộc, và tách riêng rule cho trường hợp thông tin mơ hồ giữa nhiều lựa chọn (H19 - môi trường demo) khác với trường hợp thiếu hẳn thông tin (H10, H11).   
- Điều đã học: Thiếu thông tin và thông tin mơ hồ là hai loại lỗi khác nhau, cần viết rule riêng biệt cho từng loại thì mới đo được chính xác rule nào thực sự sửa được lỗi nào.
- AI/công cụ đã dùng và cách kiểm tra: Claude dùng để phân tích run JSON (transcript thật của từng case), chẩn đoán nguyên nhân lỗi, và đề xuất patch cho system_prompt.md. Kiểm tra bằng cách chạy lại run_eval.py sau mỗi lần sửa, so sánh case_accuracy và PASS/FAIL từng case trước-sau.
- Thời điểm đã tự nộp URL repo chung trên VLearn: 20:55, 15/9/2026

### Nguyen Minh Quan — 2A202602490

- Phần việc và file/commit/PR: Viết 10 test case nhóm vào `data/eval_group.json` (5 một lượt + 5 nhiều lượt).
- Quyết định, khó khăn và cách xử lý: Khó nhất là viết case có hành vi kỳ vọng đủ rõ ràng để hệ thống chấm đúng/sai tự động, tránh case mơ hồ dẫn đến kết quả không đáng tin cậy. Quyết định bám sát các loại lỗi thật đã quan sát được ở bộ eval gốc (routing, tham số, boundary xác nhận) để 10 case mới thực sự kiểm tra được hành vi có ý nghĩa.
- Điều đã học: Một bộ test case tốt cần phản ánh đúng các lỗi thực tế đã gặp, không chỉ viết case dễ đoán kết quả.
- AI/công cụ đã dùng và cách kiểm tra: Claude dùng để hỗ trợ sinh testcase/ kiểm chứng test case dùng run-eval.py
- Thời điểm đã tự nộp URL repo chung trên VLearn: 20:55, 15/9/2026

### Hoang Anh Tu — 2A202602643

- Phần việc và file/commit/PR: Sửa `system_prompt.md` fix wrong_tool case H17.
- Quyết định, khó khăn và cách xử lý: Case này ban đầu bị hiểu nhầm là lỗi chọn sai tool, nhưng đọc kỹ log thì agent chọn đúng cả 3 tool, chỉ sai tham số check (dùng "all" thay vì "vpn"). Quyết định sửa rule để yêu cầu agent set đúng tham số check khớp với phần cụ thể được hỏi, thay vì mặc định "all" khi gọi nhiều tool song song.
- Điều đã học: Lỗi "wrong_tool" không phải lúc nào cũng do chọn sai tool — cần đọc kỹ observed_mismatch trong log để chẩn đoán đúng nguyên nhân gốc trước khi sửa prompt, tránh sửa nhầm chỗ.
- AI/công cụ đã dùng và cách kiểm tra: Claude dùng để phân tích run JSON (transcript thật của từng case), chẩn đoán nguyên nhân lỗi, và đề xuất patch cho system_prompt.md. Kiểm tra bằng cách chạy lại run_eval.py sau mỗi lần sửa, so sánh case_accuracy và PASS/FAIL từng case trước-sau.
- Thời điểm đã tự nộp URL repo chung trên VLearn: 20:55, 15/9/2026  