import requests
import json

# 天气API基础URL
BASE_URL = "http://t.weather.sojson.com/api/weather/city/"

# 城市与编号映射表
CITY_DATA = {
    "北京": "101010100",
    "上海": "101020100",
    "重庆": "101040100",
    "杭州": "101210101",
    "厦门": "101230201"
}

def get_city_id(city_name):
    """根据城市名查找对应的天气API编号"""
    return CITY_DATA.get(city_name)

def get_weather_data(city_id):
    """获取城市天气数据"""
    url = BASE_URL + str(city_id)
    try:
        r = requests.get(url, timeout=5)
        data = json.loads(r.text)
        if data['status'] == 200:
            city = data['cityInfo']['city']
            weather = data['data']['forecast']
            return city, weather
        else:
            print("❌ 获取天气失败:", data.get('msg', '未知错误'))
            return None, None
    except Exception as e:
        print(f"⚠️ 请求出错: {e}")
        return None, None

def format_weather_info(city, weather):
    """格式化天气信息为可读字符串"""
    all_day = []
    for i in range(6):  # 只取前6天预报
        content = weather[i]
        every_day = []

        if i == 0:
            every_day.append(f"{city}天气情况:")
        every_day.append(f"📅 {content['ymd']} {content['week']}")
        every_day.append(f"🌡️ 温度: {content['high']} / {content['low']}")
        every_day.append(f"🌬️ 风向风速: {content['fx']}: {content['fl']}")
        every_day.append(f"☁️ 天气类型: {content['type']} AQI: {content['aqi']}")
        every_day.append(f"📝 提示: {content['notice']}")

        all_day.append(every_day)

    content_send = ""
    for day in all_day:
        for line in day:
            content_send += line + "\n"
        content_send += "\n"

    return content_send.strip()

def get_weather_info(city_name):
    """
    根据城市名获取并格式化天气信息
    参数：
        city_name (str): 城市名称
    返回：
        str: 格式化后的天气信息
    """
    city_id = get_city_id(city_name)
    if not city_id:
        return f"❌ 未找到城市: {city_name}"

    city, weather = get_weather_data(city_id)
    if not city or not weather:
        return f"❌ 无法获取 {city_name} 的天气信息"

    return format_weather_info(city, weather)

# 示例调用
if __name__ == '__main__':
    result = get_weather_info("杭州")
    print('--------------------')
    print(result)
