# AppNho Lottery Source Test — tự động hóa báo cáo

Bộ này **chỉ kiểm tra khả năng truy cập các trang nguồn ứng viên** cho XSMB, XSMT, XSMN và Vietlott. Đây chưa phải hệ thống thu thập/xác minh kết quả trúng thưởng để xuất bản.

## Cách cài đặt (làm một lần)

1. Tạo repository GitHub mới, ví dụ `appnho-lottery-test`.
2. Upload toàn bộ nội dung thư mục dự án lên branch `main`, bao gồm `.github/workflows/check-lottery-sources.yml`.
3. Vào **Settings → Actions → General → Workflow permissions**, chọn **Read and write permissions**, rồi lưu. Workflow cần quyền ghi báo cáo vào repository.
4. Mở **Actions → Check lottery data sources → Run workflow** để chạy thử ngay.
5. Sau lần chạy, workflow tự cập nhật `reports/source-status.json` trong repository. Không cần tải artifact hoặc upload file thủ công.
6. Để index tự tải báo cáo: vào **Settings → Pages**; chọn **Deploy from a branch**, branch `main`, folder `/(root)`, rồi Save.
7. Mở URL GitHub Pages được GitHub cung cấp. `index.html` sẽ tự tải báo cáo và kiểm tra lại mỗi 5 phút. GitHub Actions tự chạy theo lịch mỗi 6 giờ, kể cả khi máy tính của bạn tắt.

## Những gì tự động

- Kiểm tra mã HTTP, thời gian phản hồi, từ khóa và chuỗi số cơ bản trong trang HTML.
- Ghi báo cáo vào `reports/source-status.json` và commit khi có thay đổi.
- Trang `index.html` tự tải báo cáo cùng website, không yêu cầu tải file JSON.
- Có thể bấm **Tải báo cáo ngay** để tải lại báo cáo; hoặc bấm **Mở GitHub Actions** để chạy workflow thủ công.

## Giới hạn quan trọng

- Lịch GitHub Actions có thể trễ; chu kỳ 6 giờ chỉ để kiểm tra khả năng truy cập nguồn, không phù hợp để cập nhật kết quả xổ số theo thời gian thực.
- `candidate_accessible` chỉ là ứng viên truy cập được, không xác minh các con số là kết quả chính xác, không bảo đảm cấu trúc ổn định và không xác nhận quyền tái sử dụng dữ liệu.
- Nếu nguồn chặn GitHub Actions, báo cáo sẽ thể hiện lỗi truy cập. Không được coi lỗi nguồn là kết quả xổ số.
- Mở `index.html` bằng `file://` có thể khiến trình duyệt chặn `fetch` JSON. Dùng URL GitHub Pages để tự động đọc báo cáo; tải JSON thủ công chỉ là phương án dự phòng.
- Gói này dùng Python standard library và GitHub Actions; không cần API key hay dịch vụ trả phí, nhưng vẫn tuân theo hạn mức/điều khoản của GitHub.
