from typing import List, Dict 

KEYWORD = {
    "TBI": ["TBI", "Trading Behavior Index"],
    "PPA": ["PPA", "Personal Psychological Assessment"]
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
