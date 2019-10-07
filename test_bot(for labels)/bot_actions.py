#use slot, database information to return a response
#can call api here or perform request

actions = {
    "bot.greet.formal":"您好，欢迎光临唯洛社保，很高兴为您服务。本店现在可以代缴上海、北京、长沙、广州、苏州、杭州、成都的五险一金。请问需要代缴哪个城市的呢？需要从几月份开始代缴呢？ 注意：社保局要求已怀孕的客户（代缴后再怀孕的客户不受影响）和重大疾病或者慢性病状态客户，我司不能为其代缴社保，如有隐瞒恶意代缴的责任自负！请注意参保手续开始办理后，无法退款。",
    "bot.greet.informal":"在的亲，有什么能帮助您的",
    "bot.request.hasAcc":"亲在上海有社保账户的吗",
    "bot.inform.fee":"目前政策：每月社保最低缴费2035.8元（按最低基数4699），公积金338元（按基数2420），服务费两项一起80元； 注意：小店代缴社保为微利服务，所以不能用信用卡支付。如果需要用信用卡，要额外支付一倍的手续费哦，谢谢亲的配合~"
}

class ACTION():
    def __init__(self):
        self.template = actions

    def fetch_response(self,key):
        return self.template[key]

if __name__ == "__main__":
    a = ACTION()
    print(a.fetch_response("bot.greet.formal"))