STR_DIGITSET = {"0","1","2","3","4","5","6","7","8","9","."}
CHI_DIGITSET = {"一","二","三","四","五","六","七","八","九","十","百","千","万","亿"}
REPLACE_SET = {"？":"?","~":"-"} # From: To
STOPWORDS = {"的","了","呢","得","着","而且"}

def is_a_number(thing):
    if not isinstance(thing, str):
        try:
            w = str(thing)
        except Exception as e:
            print("<CHECK NUMBER>",e)
    else:
        w = thing
    
    # Check each character
    for char in w:
        if not char in STR_DIGITSET:
            return False

    return True

def preprocess_sequence(sequence):
    out = ""
    seq = remove_stopwords(sequence)
    for char in seq:
        if char in REPLACE_SET:
            new_char = REPLACE_SET.get(char,char)
            out = out + new_char
        else:
            out = out + char
    
    return out

def postprocess_sequence(sequence):
    o = replace_number_tokens(sequence)
    return o

def replace_number_tokens(seq):
    number_token = "_123"
    out = []
    for token in seq:
        if is_a_number(token):
            out.append(number_token)
        else:
            out.append(token)
        
    return out

def remove_stopwords(seq):
    out = ""
    for char in seq:
        if not char in STOPWORDS:
            out = out + char
    return out

# Test suite    
test_set = [
    ("1月份社保已经缴纳了吗","ask_shebao_status"),
    ("[link]有人吗","greet"),
    ("我在上海，以前交过","inform"),
    ("上海的以前没交过","inform"),
    ("我在北京，不是首次","inform"),
    ("苏州的，之前有开户口","inform"),
    ("我之前有开户口","inform"),
    ("加上一金的话？","inform"),
    ("6月份的话？","inform"),
    ("12000","inform"),
    ("12月呢？","inform"),
    ("哦，没开过户口","inform"),
    ("嗯没有交公积金","inform"),
    ("支付过了哦","inform_paid"),
    ("[link]已经付好啦","inform_paid"),
    ("费用已付注意查收","inform_paid"),
    ("我已经交过了，你看一下","inform_paid"),
    ("哦好滴，了解","affirm"),
    ("喔好的","affirm"),
    ("之前交的社保可以补吗","ask_can_topup"),
    ("成都社保可不可以补缴？","ask_can_topup"),
    ("社保可不可以补缴？","ask_can_topup"),
    ("以前缴的公积金能补吗","ask_can_topup"),
    ("社保加公积金上海的一个月差不多要多少","ask_how_much"),
    ("服务费怎么算","ask_how_much"),
    ("那么，每月要付多少？","ask_how_much"),
    ("你们可以看到成功了吗","ask_shebao_status"),
    ("社保公积金一起做收多少服务费啊","ask_how_much"),
    ("请问多久才到账", "ask_turnaround_time"),
    ("一般要多久才交上", "ask_turnaround_time"),
    ("交上社保要等多久", "ask_turnaround_time"),
    ("社保基数用8000的","ask_custom_jishu"),
    ("可以不要按照最低的吧","ask_custom_jishu"),
    ("按照12000的","ask_custom_jishu"),
    ("社保交了之后可以改基数吗？","ask_custom_jishu"),
    ("怀孕了还可以代缴吗","query_pregnant"),
    ("怀孕了还可以买吗","query_pregnant"),
    ("是在淘宝上拍那个吗","query_how_settle"),
    ("直接拍就可以了吧","query_how_settle"),
    ("怎么去拍啊","query_how_settle"),
    ("我要交本月社保杭州的，请问怎么去下单","query_how_settle"),
    ("接着怎么去拍呢","query_how_settle"),
    ("我该拍哪个？","request_link"),
    ("有没有链接？","request_link"),
    ("拍哪个宝贝？","request_link"),
    ("啥时间发货","query_fahuo"),
    ("一般会什么时间发货呢","query_fahuo"),
    ("可以延迟发货吗","query_delay_fahuo"),
    ("我想在北京买房","query_housing"),
    ("其实我是想购房的","query_housing"),
    ("这个会影响购房么？","query_housing"),
    ("落户苏州","luohu"),
    ("落户可以办理吗","luohu"),
    ("我要交杭州社保落户用的","luohu"),
    ("我不太懂哦","confused"),
    ("你说了啥？","confused"),
    ("说啥？？", "confused"),
    ("没了，谢谢","deny"),
    ("你们公司在几号截止的呢","query_pay_date"),
    ("你们一般什么时候下单？","query_pay_date"),
    ("深圳的还可以交吗","query_pay_deadline"),
    ("这个月还可以下单吗","query_pay_deadline"),
    ("首次要提供什材料吗？","query_req_resources"),
    ("需要我提供什东西吗","query_req_resources"),
    ("要参保的话需要什么资料","query_req_resources"),
    ("要啥材料吗","query_req_resources"),
    ("什么时候能查到","query_when_check_shebao_status"),
    ("要多久能查到呢？","query_when_check_shebao_status"),
    ("请问可以代缴上海社保吗","purchase"),
    ("我想交11月社保不断的可以吗","purchase"),
    ("我准备离职中间两个月不交社保。这里可以帮我代缴吗","purchase"),
    ("我是想要代缴9月的","purchase"),
    ("想要代缴昆山社保的","purchase"),
    ("这里能代缴广州五险一金吗","purchase"),
    ("我可不可以用花呗来下单啊","query_use_huabei"),
    ("方便用电话讲吗","query_phone"),
    ("请问流程是怎么样的？","query_pay_process"),
    ("你们交社保的流程是怎么样？","query_pay_process"),
    ("怎么看到缴纳记录？","query_how_check_shebao_status"),
    ("缴纳之后能查看记录吗？","query_how_check_shebao_status"),
    ("在哪里能查到社保","query_how_check_shebao_status"),
    ("怎么去查社保有没有交上了","query_how_check_shebao_status"),
    ("怎么查杭州社保是否交了","query_how_check_shebao_status"),
    ("你们是交哪几个区的","query_region_coverage"),
    ("可以搞什么区啊","query_region_coverage"),
    ("可以同时代缴两地吗", "query_multiple_locations"),
    ("能交两个地方的社保吗", "query_multiple_locations"),
    ("下月还得这里拍吗","query_xufei"),
    ("下次只要拍这个吧","query_xufei"),
    ("交续费也这样拍吗","query_xufei"),
    ("我真的很爱您哦","complicated"),
    ("我这个月失业了还能继续代缴吗","complicated"),
    ("外地人能交社保吗","complicated"),
    ("不是500吗怎么变了1000呢？","complicated"),
    ("您好我这个月离职","complicated"),
    ("我给朋友推荐了你们公司","complicated"),
    ("会有什么影响吗？","query_various_effects"),
    ("有什么后果吗？","query_various_effects"),
    ("不缴公积金会有什么影响啊","query_various_effects"),
    ("断了会怎么样吗","query_break"),
    ("费用为啥80","doublecheck_value"),
    ("这个1937是包括费用么","doublecheck_value"),
    ("1000是吧","doublecheck_value"),
    ("生病之后去办理医保可以吗","query_sick"),
    ("参保可以吗 我现在住院","query_sick"),
    ("看病没关系吧","query_sick_light"),
    ("若出问题，及时联系","request_notify"),
    ("好了就联系我哦","request_notify"),
    ("[link]如果有什么事及时联系我","request_notify"),
    ("如果那边有什么问题要及时通知我哦","request_notify"),
    ("[link]我还需要给什么资料吗","query_req_resources"),
    ("要社保卡是怎么办理","query_shebao_card"),
    ("请问公积金卡怎么去弄的","query_gjj_card"),
    ("交这个月续费","purchase_xufei"),
    ("几号可以开户？","query_when_kaihu"),
    ("减员是什么意思呀","define"),
    ("你们的公司叫什么名啊","query_company_name"),
    ("然后？","next_step"),
    ("弄好了哈","inform_done")
]

def get_test_set():
    test_x = []
    test_y = []
    for pair in test_set:
        x,y = pair
        test_x.append(x)
        test_y.append(y)
    return (test_x, test_y)

if __name__ == "__main__":
    result = int(0.8655 * len(test_set))
    print(result, "/",len(test_set))