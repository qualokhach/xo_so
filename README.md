# AppNho Lottery Source Test

Bộ thử nghiệm khả năng truy cập các trang ứng viên cho XSMB, XSMT, XSMN và Vietlott. Đây **chưa phải** hệ thống tự thu thập kết quả xổ số để xuất bản.

## Mở trang index

Mở `index.html` bằng trình duyệt. Trang giúp bạn xem báo cáo JSON sau khi chạy kiểm tra và có liên kết đến các trang nguồn. Không cần cài đặt máy chủ để xem giao diện.

## Chạy kiểm tra thật bằng GitHub Actions

1. Tạo một repository GitHub mới, ví dụ `appnho-lottery-test`.
2. Upload toàn bộ nội dung thư mục dự án lên repository, bao gồm thư mục `.github` (nếu giao diện web không hiện file ẩn, hãy đảm bảo `.github/workflows/check-lottery-sources.yml` được upload).
3. Vào tab **Actions** → **Check lottery data sources** → **Run workflow**.
4. Mở lần chạy mới nhất và tải artifact `appnho-lottery-source-report`.
5. Giải nén artifact, lấy `source-status.json`, rồi mở `index.html` và chọn file JSON để xem kết quả.

Workflow cũng được đặt lịch chạy mỗi 6 giờ. GitHub Actions có thể trễ lịch và không đảm bảo chạy đúng từng phút.

## Những gì script kiểm tra

- Có tải được trang qua HTTP hay không.
- Mã HTTP, loại nội dung, thời gian phản hồi.
- Một số từ khóa và chuỗi số cơ bản có xuất hiện trong nội dung HTML hay không.

Kết quả `candidate_accessible` chỉ có nghĩa là trang vượt qua kiểm tra sơ bộ. Nó **không** xác minh các con số là kết quả xổ số chính xác, không bảo đảm cấu trúc trang sẽ ổn định, và không xác nhận quyền tái sử dụng dữ liệu. Cần kiểm tra nguồn chính thức, điều khoản truy cập, và đối chiếu kết quả trước khi dùng cho website thật.

## Lưu ý

- Mở `index.html` không tự chạy script Python; trình duyệt thường chặn truy vấn trực tiếp tới website khác do CORS. Hãy dùng GitHub Actions để kiểm tra nguồn từ máy chủ runner.
- Script dùng Python standard library, không cần API key.
- Không có dịch vụ trả phí nào được cấu hình trong gói này. Việc sử dụng GitHub Actions vẫn tuân theo hạn mức và điều khoản của GitHub.
