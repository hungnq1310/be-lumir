from typing import List, Dict 

KEYWORD ={    
    "TBI": ["TBI", "Trading Behavior Index"],
    "EDI": ["Emotional Drive Index" , "chỉ số này phản ánh khát khao hành vi sâu thẳm chi phối quyết định giao dịch. Nó lý giải cách trader phản ứng với thị trường và áp lực cảm xúc."],
    "PPAI": ["Path Potential Alignment Index", "đo lường mức độ liên kết giữa hành trình hành vi gốc (Path) và vai trò tiềm năng cần đạt (Potential). Chỉ số này cho trader biết những hành vi nào cần rèn luyện và điều chỉnh để vừa tốt nghiệp được bài học hành vi cốt lõi, vừa hoàn thành sứ mệnh giao dịch và tiến hóa thành phiên bản Elite Trader."],
    "SPI": ["Skill Potential Index", "cho thấy vai trò hành vi cốt lõi mà một trader cần phát huy để đạt đỉnh cao trong giao dịch. Khi bạn hoàn thiện chỉ số này bạn sẽ vừa thỏa mãn đam mê, vừa tạo ra tác động tích cực trong cộng đồng trader. Chỉ số SPI không chỉ phản ánh điểm mạnh hiện tại, mà còn chỉ ra năng lực tiềm ẩn cần khai thác để trở thành Elite Trader."],
    "CMI": ["Crisis Management Index", "phản ánh cách trader ứng phó với khó khăn và áp lực trong giao dịch. Chỉ số này cho biết khả năng giữ vững sự tỉnh táo, phân tích tình huống và lựa chọn hành động đúng đắn khi thị trường biến động."],
    "MPI": ["Market Persona Index", "phản ánh cách trader được thị trường và cộng đồng nhìn nhận thông qua hành vi, năng lượng và phong cách giao dịch mà họ thể hiện ra ngoài. Chỉ số này giúp trader phát đi tín hiệu tính cách tới thế giới và nhận biết mức độ nhất quán giữa bản chất bên trong và hình ảnh bên ngoài."],
    "RI": ["Resilience Index", "phản ánh giai đoạn bạn đạt độ chín trong tư duy và sức bền giao dịch. Chỉ số này cho biết thời điểm năng lượng, trải nghiệm và khả năng kiểm soát rủi ro được phát huy mạnh mẽ nhất, tập trung vào chiến lược, kỷ luật và quản trị vốn."],
    "IOCI": ["Inner Outer Coherence Index", "đo lường mức độ hòa hợp giữa động lực nội tâm và cách bạn thể hiện ra bên ngoài trong giao dịch. IOCI giúp trader duy trì sự nhất quán, giảm hiểu lầm và củng cố niềm tin giữa bản thân và cộng đồng."],
    "TAI": ["Trading Attitude Index", "phản ánh thái độ và góc nhìn cốt lõi mà trader mang vào thị trường, cho thấy cách tiếp nhận tình huống, cơ hội và rủi ro để duy trì kỷ luật, tập trung và thái độ tích cực."],
    "PPA": ["Path Potential Alignment", "là chỉ số cốt lõi phản ánh con đường phát triển tự nhiên của trader, cho biết mục tiêu, phong cách hành vi nổi bật, rào cản và bài học lớn cần vượt qua để đạt sự ổn định và bền vững."],
    "WMI": ["Weakness Map Index", "phản ánh những hành vi giao dịch và năng lực tâm lý mà trader chưa được trang bị bẩm sinh, giúp xác định điểm yếu cần rèn luyện để hoàn thiện bản thân."],
    "SSI": ["Subconscious Stability Index", "phản ánh nền tảng hành vi vô thức giúp trader duy trì ổn định khi đối mặt với áp lực thị trường và chuỗi biến động bất lợi, thể hiện khả năng phục hồi và kỷ luật tâm lý."],
    "SAI": ["Strength Amplifier Index", "phản ánh nguồn năng lượng tiềm ẩn thúc đẩy hành vi giao dịch, có thể là sức mạnh hoặc cạm bẫy tùy cách kiểm soát."],
    "NEI": ["Natural Edge Index", "phản ánh lợi thế tự nhiên của trader về bản năng, kỹ năng bẩm sinh và sức mạnh hành vi đặc trưng, giúp xác định môi trường giao dịch phù hợp nhất để phát huy điểm mạnh."],
    "BLI": ["Behavioral Liability Index", "phản ánh những bài học hành vi mà trader cần nhận diện và vượt qua trong quá trình phát triển để tránh lặp lại sai lầm."],
    "ARI": ["Analytical Reasoning Index", "phản ánh khả năng phân tích dữ liệu, đánh giá rủi ro và ra quyết định logic trong điều kiện thị trường biến động mạnh."],
    "TCI": ["Trading Cycle Index", "phản ánh các giai đoạn phát triển quan trọng của trader, nơi kỹ năng và năng lượng được thử thách để tạo nên bước nhảy vọt trong hành trình giao dịch."],
    "MRI": ["Monthly Rhythm Index", "phản ánh nhịp độ hành vi và năng lượng trong từng giai đoạn 30 ngày, giúp trader xác định thời điểm nên mở rộng hành động hay chậm lại để củng cố hệ thống."],
    "DAI": ["Daily Alignment Index", "phản ánh mức độ phù hợp giữa trạng thái hành vi cá nhân và nhịp thị trường trong từng ngày, gợi ý hoạt động phù hợp như quan sát, học hỏi, review hay hành động."],
    "CII": ["Cohort Influence Index", "phản ánh ảnh hưởng của bối cảnh thế hệ và môi trường thị trường tới phong cách giao dịch, giúp trader thích nghi tốt hơn và vẫn giữ bản sắc cá nhân."],
    "AMI": ["Annual Momentum Index", "phản ánh nhịp độ hành vi và năng lượng hàng năm, giúp trader xác định trọng tâm phát triển phù hợp như kỷ luật, chiến lược hay mở rộng quy mô giao dịch."],
    "BCI": ["Behavioral Challenge Index", "phản ánh khó khăn trong việc duy trì kỷ luật và hành vi đúng khi thị trường thay đổi, giúp nhận diện nút thắt để thiết kế thử thách coaching phù hợp."],
    

    # Traidng keyword
    "total_trades": ['Tổng số lệnh đã được thực hiện trong giai đoạn theo dõi.', "Phản ánh mức độ hoạt động của trader hoặc hệ thống. Số lượng lớn cho thấy tần suất giao dịch cao, dùng để đánh giá hiệu suất, tỉ lệ thắng, và chất lượng chiến lược." ],
    "today_balance": ["Số dư tài khoản hiện tại sau khi kết thúc ngày giao dịch.", "Thể hiện giá trị tài khoản thực tế bao gồm cả lời/lỗ của ngày hiện tại; dùng để theo dõi biến động vốn hằng ngày."],
     "net_profit_before_today": [
    "Tổng lợi nhuận hoặc thua lỗ tích lũy trước ngày hiện tại.",
    "Cho biết hiệu suất tổng thể trước khi tính các kết quả của ngày hôm nay, giúp đánh giá xu hướng lời/lỗ trong giai đoạn dài hơn."
  ],
    "net_profit_today": [
        "Lợi nhuận hoặc thua lỗ ròng phát sinh trong ngày hiện tại.",
        "Đo lường kết quả giao dịch trong ngày, giúp kiểm soát hiệu suất ngắn hạn và phản ứng thị trường."
    ],
    "today_permitted_loss": [
        "Giới hạn lỗ tối đa được phép trong ngày.",
        "Công cụ kiểm soát rủi ro hằng ngày; khi lỗ vượt mức này, hệ thống hoặc trader phải dừng giao dịch để bảo toàn vốn."
    ],
    "max_permitted_loss": [
        "Giới hạn lỗ tối đa tổng cộng kể từ đầu kỳ hoặc giai đoạn giao dịch.",
        "Mức sàn bảo vệ tài khoản khỏi rủi ro sụp đổ; nếu chạm giới hạn này, tài khoản sẽ bị ngưng hoạt động hoặc reset."
    ],
    "balance_init": [
        "Số vốn khởi điểm của tài khoản khi bắt đầu giao dịch.",
        "Là cơ sở để tính drawdown, lợi nhuận %, và quy mô rủi ro. Mọi chỉ số hiệu suất đều quy chiếu về giá trị này."
    ],
    "balance_size": [
        "Phân loại quy mô tài khoản (mini, standard, pro, v.v.) hoặc dung lượng vốn quản lý.",
        "Giúp xác định hạn mức giao dịch, khối lượng lệnh, và cách áp dụng chiến lược quản lý rủi ro."
    ],
    "start_time": [
        "Thời điểm bắt đầu giai đoạn theo dõi hoặc kích hoạt tài khoản.",
        "Giúp xác định thời gian hoạt động, tính lợi nhuận trung bình theo ngày, và tốc độ tăng trưởng tài khoản."
    ],
    "last_updated_time": [
        "Thời điểm dữ liệu được cập nhật gần nhất.",
        "Cho biết tính mới của dữ liệu; quan trọng trong các dashboard theo dõi hoặc hệ thống risk engine thời gian thực."
    ]
}
def get_keywords(keyword_list: List[str]) -> Dict[str, str]:
    global KEYWORD
    try:
        result = {}
        for key in keyword_list:
            if key in KEYWORD:
                result[key] = KEYWORD[key]
            else:
                result[key] = "not found"
        return result
    except Exception as e:
        return {"error": str(e)}



if __name__ == "__main__":
    print(get_keywords(["TBI", "PPA", "XYZ"]))
