"""
CJK word segmenter for TextHumanize.

Supports Chinese (BiMM), Japanese (char-type),
and Korean (space + particle separation).
No external dependencies.
"""

from __future__ import annotations

import logging
import unicodedata

logger = logging.getLogger(__name__)

# ── Chinese dictionary ─────────────────────────────
# Built as a frozenset for O(1) lookup.
# Max word length for FMM/BMM: 7 characters.

_ZH_MAX_WORD = 7

# Function words / particles
_ZH_FUNC = (
    "的,了,着,过,地,得,把,被,给,让,向,对,在,从,到,"
    "吗,吧,呢,啊,呀,哦,嘛,哇,啦,喔,哈,嗯,噢,"
    "之,其,所,而,则,且,乃,以,于,与,及"
)

# Pronouns
_ZH_PRON = (
    "我,你,他,她,它,我们,你们,他们,她们,它们,"
    "自己,大家,别人,人家,各自,彼此,本人,某人,"
    "谁,什么,哪,哪里,哪些,怎么,怎样,如何,"
    "这,那,这个,那个,这些,那些,这里,那里,"
    "这样,那样,这种,那种,这么,那么"
)

# Common verbs (2-char)
_ZH_VERB2 = (
    "工作,学习,使用,开始,结束,发展,研究,认为,"
    "发现,提供,进行,实现,建立,成为,表示,参加,"
    "决定,讨论,分析,完成,推动,提高,增加,减少,"
    "保持,坚持,支持,反对,帮助,影响,解决,处理,"
    "管理,控制,改善,改变,创造,组织,需要,知道,"
    "了解,希望,相信,感觉,觉得,喜欢,愿意,打算,"
    "考虑,准备,试图,继续,停止,允许,拒绝,承认,"
    "否认,证明,保证,确保,促进,加强,扩大,缩小,"
    "降低,提升,推进,引导,实施,执行,开展,参与,"
    "合作,交流,沟通,介绍,说明,记录,观察,比较,"
    "评估,检查,调查,测试,设计,制定,规划,选择,"
    "注意,强调,指出,报告,计算,培养,采用,运用,"
    "利用,发挥,体现,反映,代表,包括,涉及,涵盖,"
    "属于,存在,出现,产生,形成,构成,组成,导致,"
    "引起,造成,获得,取得,达到,满足,超过,保护,"
    "维护,修复,调整,优化,整合,开发,探索,创建,"
    "删除,修改,更新,发布,传播,推广,宣传,鼓励,"
    "激励,启发,引领,带动,协调,配合,负责,承担,"
    "面临,遭受,经历,体验,享受,接受,拒绝,抵制,"
    "抗议,呼吁,倡导,主张,认定,界定,定义,概括,"
    "描述,刻画,展示,呈现,揭示,阐述,论证,解释,"
    "说服,争论,辩护,批评,赞扬,表扬,鼓掌,欢迎,"
    "告别,道歉,感谢,称赞,评价,判断,推测,猜测,"
    "预测,预计,期待,盼望,渴望,追求,寻找,搜索,"
    "发掘,挖掘,收集,整理,汇总,分类,归纳,总结,"
    "排列,安排,部署,配置,分配,指定,委托,授权,"
    "批准,审批,审核,审查,审议,通过,颁布,实行,"
    "执法,监督,指导,培训,教育,教学,辅导,咨询"
)

# Common nouns (2-char)
_ZH_NOUN2 = (
    "时间,问题,方法,系统,技术,信息,数据,社会,"
    "经济,教育,文化,历史,科学,政治,国家,世界,"
    "地方,城市,学校,公司,市场,产品,服务,质量,"
    "环境,资源,能力,水平,效果,结果,过程,作用,"
    "条件,情况,关系,原因,目的,方式,方向,标准,"
    "内容,特点,优势,趋势,价值,意义,未来,基础,"
    "经验,知识,思想,理论,观点,态度,精神,力量,"
    "意识,责任,安全,健康,生活,建设,改革,创新,"
    "工程,项目,计划,任务,目标,要求,措施,政策,"
    "制度,规则,法律,权利,义务,利益,成本,效率,"
    "速度,程度,规模,范围,领域,行业,部门,机构,"
    "团队,成员,人员,专家,学者,人民,群众,干部,"
    "领导,同事,朋友,家庭,父母,孩子,老师,学生,"
    "医生,护士,工人,农民,军人,警察,记者,作家,"
    "歌手,演员,导演,画家,网络,手机,电话,电脑,"
    "电视,报纸,杂志,书籍,文章,论文,报告,文件,"
    "材料,资料,档案,证据,合同,协议,声明,通知,"
    "公告,命令,决议,方案,建议,意见,评论,消息,"
    "新闻,事件,活动,会议,论坛,展览,比赛,考试,"
    "面试,培训,课程,专业,学科,学位,证书,资格,"
    "职位,岗位,薪酬,福利,假期,工资,收入,利润,"
    "税收,预算,投资,贸易,出口,进口,需求,供给,"
    "竞争,垄断,风险,危机,挑战,机遇,战略,策略,"
    "模式,机制,体制,框架,结构,层次,阶段,步骤,"
    "环节,因素,变量,指标,数量,比例,概率,频率,"
    "面积,体积,重量,温度,密度,压力,高度,深度,"
    "距离,位置,空间,区域,地区,省份,城镇,乡村,"
    "街道,建筑,住宅,设施,设备,工具,仪器,材质,"
    "能源,石油,天然,电力,交通,铁路,公路,航空,"
    "港口,车辆,飞机,轮船,火车,地铁,食品,药品,"
    "农业,工业,商业,旅游,体育,音乐,电影,艺术,"
    "宗教,哲学,心理,语言,数学,物理,化学,生物,"
    "医学,法学,网站,平台,软件,硬件,程序,算法,"
    "模型,接口,功能,性能,用户,客户,消费,生产"
)

# AI / formal phrases
_ZH_FORMAL = (
    "鉴于,根据,因此,然而,此外,总之,综上所述,"
    "换言之,值得注意,不可否认,毫无疑问,"
    "与此同时,在这方面,具有重要意义,"
    "发挥重要作用,采取有效措施,进一步加强,"
    "不断完善,充分发挥,积极推进,全面提高,"
    "切实加强,深入推进,着力解决,努力实现,"
    "大力推进,有效促进,持续推进,扎实推进,"
    "统筹推进,从某种程度上说,坚定不移,"
    "行之有效,卓有成效,富有成效,有目共睹,"
    "众所周知,不言而喻,显而易见,不容忽视,"
    "至关重要,举足轻重,肩负重任,责无旁贷,"
    "义不容辞,当务之急,重中之重,首当其冲,"
    "归根结底,一言以蔽之,综合考虑,统筹兼顾,"
    "与时俱进,开拓进取,锐意进取,勇于创新,"
    "大胆探索,先行先试,典型经验,有益探索"
)

# Adjectives
_ZH_ADJ = (
    "重要,主要,不同,相关,具体,明确,有效,基本,"
    "一般,特殊,正常,必要,合理,适当,严格,良好,"
    "优秀,突出,显著,明显,巨大,广泛,深入,全面,"
    "积极,主动,成功,困难,简单,复杂,丰富,多样,"
    "稳定,灵活,先进,现代,传统,最新,真正,实际,"
    "详细,完整,准确,正确,清楚,模糊,客观,主观,"
    "直接,间接,公开,公正,公平,平等,独立,统一,"
    "共同,一致,连续,持续,长期,短期,永久,临时,"
    "固定,随机,自动,手动,强烈,温和,激烈,缓慢,"
    "迅速,快速,高效,低效,普遍,罕见,常见,典型,"
    "特定,唯一,绝对,相对,潜在,显在,隐含,外在"
)

# Adverbs
_ZH_ADV = (
    "已经,正在,将要,可以,应该,必须,可能,非常,"
    "十分,特别,尤其,更加,最,很,太,比较,相当,"
    "几乎,完全,确实,果然,终于,仍然,依然,始终,"
    "一直,不断,逐步,逐渐,立即,马上,已,曾,刚,"
    "又,再,还,也,都,只,就,才,却,便,即,并,"
    "均,皆,总,常,每,永,仅,略,稍,颇,甚,极,"
    "越,愈,更,较,最,顶,格外,往往,时常,经常,"
    "通常,一般,大概,大约,大致,基本上,总共,"
    "一共,至少,至多,恰好,刚好,正好,偏偏,竟然,"
    "居然,简直,的确,到底,究竟,毕竟,难道,何必,"
    "何况,况且,反正,分明,明明,显然,当然,自然"
)

# Connectors
_ZH_CONN = (
    "并且,而且,但是,或者,如果,虽然,因为,所以,"
    "不过,于是,因而,从而,进而,以便,以免,否则,"
    "无论,不管,只要,只有,除非,除了,尽管,即使,"
    "哪怕,一旦,既然,由于,为了,关于,对于,至于,"
    "按照,通过,随着,沿着,依据,基于,鉴于,针对,"
    "围绕,结合,凭借,借助,以及,或是,而是,还是,"
    "不仅,而且,既,又,又,要么,不但,不仅仅,"
    "与其,宁可,宁愿,假如,倘若,万一,一旦"
)

# 3+ char compounds
_ZH_COMPOUND = (
    "互联网,计算机,大数据,人工智能,机器学习,"
    "信息化,现代化,国际化,标准化,专业化,多元化,"
    "全球化,社会主义,共产主义,资本主义,可持续,"
    "高质量,新时代,改革开放,科学技术,知识产权,"
    "市场经济,自然科学,社会科学,研究生,大学生,"
    "工作者,领导者,消费者,生产者,投资者,志愿者,"
    "运动员,科学家,企业家,艺术家,教育家,幼儿园,"
    "博物馆,图书馆,体育馆,办公室,实验室,研究所,"
    "委员会,有限公司,股份公司,国务院,人大代表,"
    "政协委员,共青团,少先队,基金会,协会,学会,"
    "研究院,工程师,设计师,程序员,分析师,管理员,"
    "服务器,数据库,操作系统,云计算,物联网,"
    "区块链,深度学习,自然语言,虚拟现实,增强现实,"
    "供应链,产业链,价值链,生态链,半导体,新能源,"
    "电动车,高铁,航天,航空,海洋,生态,碳中和,"
    "碳排放,可再生,不可再生,高科技,低碳,绿色,"
    "循环经济,数字经济,共享经济,经济体制,政治体制,"
    "中华民族,马克思主义,辩证法,唯物主义,方法论,"
    "世界观,人生观,价值观,习近平,新冠肺炎,"
    "公共卫生,突发事件,国有企业,民营企业,外资企业,"
    "乡镇企业,中小企业,跨国公司,合资企业,"
    "高等教育,基础教育,义务教育,职业教育,"
    "成人教育,远程教育,素质教育,终身教育,"
    "可持续发展,全面发展,和谐发展,科学发展,"
    "创新发展,协调发展,绿色发展,开放发展,"
    "共享发展,高质量发展"
)

# Single-char words
_ZH_SINGLE = (
    "人,事,物,话,天,年,月,日,时,分,点,次,"
    "种,个,些,多,少,大,小,长,短,高,低,新,"
    "老,好,坏,对,错,是,有,无,不,要,能,会,"
    "想,看,说,做,去,来,上,下,前,后,左,右,"
    "中,内,外,里,间,边,旁,方"
)

# Numbers / measures
_ZH_NUM = (
    "一,二,三,四,五,六,七,八,九,十,百,千,"
    "万,亿,零,两,几,半,双,每,各,第,初,"
    "个,只,条,本,把,张,件,位,名,台,辆,"
    "架,套,副,对,根,支,片,块,瓶,杯,碗,"
    "盘,包,箱,层,排,栋,间,所,座,家,户,"
    "群,批,组,项,股,笔,门,节,章,页,行,"
    "段,篇,首,部,册,卷,期,届,轮,场,回,"
    "遍,趟,圈,米,公里,厘米,毫米,公斤,吨,"
    "克,升,毫升,平方,立方,公顷,亩,元,角,"
    "分钱,美元,欧元,英镑,日元,韩元,秒,度,"
    "岁,倍,成,分之"
)

# Extra common 2-char that may not be above
_ZH_EXTRA2 = (
    "东西,南北,上下,左右,前后,大小,多少,长短,"
    "快慢,轻重,黑白,新旧,好坏,真假,内外,远近,"
    "开关,买卖,进出,收发,来往,起落,讲座,座谈,"
    "研讨,峰会,庆典,典礼,仪式,就业,失业,创业,"
    "毕业,入学,升学,转学,退学,考核,答辩,研修,"
    "进修,访问,参观,旅行,出差,度假,休息,运动,"
    "锻炼,散步,跑步,游泳,爬山,钓鱼,打球,下棋,"
    "唱歌,跳舞,画画,写字,读书,看报,上网,聊天,"
    "打车,开车,骑车,坐车,下车,上车,等车,停车,"
    "吃饭,做饭,炒菜,煮饭,洗碗,扫地,拖地,擦窗,"
    "洗衣,晒衣,熨衣,缝补,打扫,整理,收拾,搬家,"
    "装修,买房,租房,卖房,看房,选房,交房,验房,"
    "存款,取款,转账,汇款,贷款,还款,付款,收款,"
    "签字,盖章,登记,注册,申请,办理,受理,审批"
)

# Additional 2-char words to reach 600+ total
_ZH_EXTRA3 = (
    "办法,想法,看法,做法,说法,写法,用法,手法,"
    "技巧,窍门,秘密,奥秘,谜语,答案,线索,证据,"
    "根源,源头,起点,终点,出发,到达,经过,路过,"
    "通过,穿过,跨过,越过,绕过,避开,躲避,逃避,"
    "面对,应对,对付,抵抗,战胜,克服,突破,超越,"
    "赶上,追上,跟上,落后,退步,进步,提升,上升,"
    "下降,回落,反弹,波动,震荡,起伏,升降,涨跌,"
    "开盘,收盘,成交,买入,卖出,持有,抛售,套利,"
    "盈利,亏损,分红,配股,增发,回购,清算,破产,"
    "重组,兼并,收购,合并,拆分,剥离,转让,租赁,"
    "招标,投标,中标,开标,评标,定标,签约,履约,"
    "违约,解约,续约,仲裁,诉讼,起诉,应诉,上诉,"
    "裁定,判决,执行,强制,惩罚,处分,开除,辞退,"
    "辞职,退休,离休,退役,转业,复员,动员,召集"
)

# Body / health / medicine
_ZH_HEALTH = (
    "身体,心脏,大脑,肝脏,肺部,肾脏,胃部,肠道,"
    "血液,骨骼,肌肉,皮肤,神经,细胞,基因,蛋白,"
    "病毒,细菌,感染,免疫,疫苗,抗体,诊断,治疗,"
    "手术,检查,化验,处方,药物,剂量,疗效,康复,"
    "预防,保健,养生,饮食,营养,维生素,矿物质,"
    "脂肪,蛋白质,碳水化合物,纤维,热量,卡路里,"
    "体重,血压,血糖,心率,体温,症状,病因,并发,"
    "慢性,急性,恶性,良性,遗传,变异,突变,进化,"
    "门诊,住院,急诊,挂号,看病,开药,打针,输液,"
    "消毒,隔离,观察,护理,急救,抢救,复查,随访,"
    "头痛,发烧,咳嗽,感冒,过敏,中毒,骨折,烧伤,"
    "高血压,糖尿病,心脏病,癌症,肿瘤,白血病"
)

# Nature / geography / weather
_ZH_NATURE = (
    "山脉,河流,湖泊,海洋,沙漠,草原,森林,丛林,"
    "平原,盆地,高原,峡谷,岛屿,半岛,大陆,大洲,"
    "北方,南方,东方,西方,赤道,极地,热带,温带,"
    "寒带,季风,台风,暴风,暴雨,洪水,干旱,地震,"
    "火山,海啸,泥石流,雷电,冰雹,霜冻,雾霾,"
    "降雨,降雪,晴天,阴天,多云,气压,气流,风力,"
    "温度,湿度,紫外线,空气,氧气,二氧化碳,臭氧,"
    "矿产,石油,天然气,煤炭,铁矿,铜矿,金矿,"
    "钻石,宝石,珊瑚,化石,土壤,岩石,沙子,泥土,"
    "植物,动物,昆虫,鸟类,鱼类,哺乳,两栖,爬行,"
    "花朵,树木,草地,种子,果实,根茎,叶片,花粉,"
    "生态,物种,栖息,迁徙,繁殖,灭绝,濒危,保护"
)

# Food / cooking / daily life
_ZH_FOOD = (
    "米饭,面条,馒头,包子,饺子,粽子,月饼,汤圆,"
    "豆腐,豆浆,牛奶,酸奶,鸡蛋,猪肉,牛肉,羊肉,"
    "鸡肉,鱼肉,虾仁,海鲜,蔬菜,水果,苹果,香蕉,"
    "橙子,葡萄,西瓜,草莓,番茄,土豆,白菜,萝卜,"
    "黄瓜,茄子,辣椒,大蒜,生姜,大葱,花椒,酱油,"
    "味精,食盐,白糖,食醋,花生,核桃,芝麻,绿茶,"
    "红茶,咖啡,果汁,汽水,白酒,啤酒,红酒,饮料,"
    "早餐,午餐,晚餐,夜宵,零食,甜点,蛋糕,面包,"
    "饼干,巧克力,冰淇淋,火锅,烧烤,炒菜,蒸煮,"
    "油炸,煎烤,凉拌,腌制,烘焙,厨房,餐厅,食堂,"
    "菜单,点菜,上菜,买单,外卖,快递,打包,自助"
)

# Clothing / household / objects
_ZH_OBJECTS = (
    "衣服,裤子,裙子,外套,大衣,衬衫,毛衣,棉袄,"
    "鞋子,袜子,帽子,围巾,手套,领带,腰带,背包,"
    "手表,眼镜,项链,戒指,耳环,手镯,珠宝,首饰,"
    "沙发,桌子,椅子,床铺,柜子,书架,窗帘,地毯,"
    "灯泡,插座,开关,空调,冰箱,洗衣机,电饭煲,"
    "微波炉,电风扇,热水器,吸尘器,电熨斗,电水壶,"
    "钥匙,雨伞,毛巾,牙刷,牙膏,肥皂,洗发水,"
    "护肤品,化妆品,卫生纸,垃圾袋,保鲜膜,打火机,"
    "筷子,勺子,叉子,刀子,碗碟,杯子,盘子,锅具,"
    "剪刀,针线,胶带,绳子,铁丝,钉子,锤子,螺丝"
)

# Transport / travel
_ZH_TRANSPORT = (
    "汽车,公交,出租车,私家车,面包车,货车,卡车,"
    "摩托车,自行车,电动车,三轮车,拖拉机,挖掘机,"
    "火车,动车,高铁,地铁,轻轨,有轨电车,磁悬浮,"
    "飞机,直升机,客机,战斗机,运输机,无人机,"
    "轮船,游艇,帆船,快艇,渡轮,邮轮,潜艇,航母,"
    "机场,车站,码头,港口,停车场,加油站,收费站,"
    "高速公路,立交桥,隧道,天桥,人行道,斑马线,"
    "红绿灯,交通灯,限速,超速,罚款,扣分,驾照,"
    "护照,签证,海关,边检,安检,登机,起飞,降落,"
    "航班,车次,座位,卧铺,行李,托运,退票,改签,"
    "酒店,宾馆,民宿,旅馆,度假村,景区,景点,门票"
)

# Technology / internet / digital
_ZH_TECH = (
    "电脑,笔记本,台式机,平板,显示器,键盘,鼠标,"
    "打印机,扫描仪,摄像头,耳机,音箱,充电器,"
    "数据线,内存,硬盘,处理器,显卡,主板,芯片,"
    "网络,宽带,路由器,光纤,信号,频率,带宽,"
    "网页,浏览器,搜索引擎,电子邮件,即时通讯,"
    "社交媒体,短视频,直播,博客,论坛,网购,支付,"
    "二维码,条形码,密码,账号,注册,登录,下载,"
    "上传,安装,卸载,更新,升级,备份,恢复,格式,"
    "文件夹,压缩包,截图,录屏,视频,音频,图片,"
    "文档,表格,幻灯片,字体,排版,编辑,复制,粘贴,"
    "撤销,删除,搜索,替换,保存,打开,关闭,刷新,"
    "加密,解密,防火墙,杀毒,木马,漏洞,黑客,补丁"
)

# Education / academic
_ZH_EDU = (
    "幼儿园,小学,初中,高中,大学,研究生,博士生,"
    "本科,硕士,博士,学士,院士,教授,副教授,讲师,"
    "助教,导师,班主任,辅导员,校长,院长,系主任,"
    "年级,班级,学期,学年,寒假,暑假,课堂,课外,"
    "作业,考试,测验,期中,期末,高考,中考,考研,"
    "成绩,分数,及格,满分,奖学金,助学金,学费,"
    "教材,课本,参考书,习题,答题,阅卷,评分,排名,"
    "语文,数学,英语,物理,化学,生物,地理,政治,"
    "历史,音乐,美术,体育,计算机,外语,选修,必修,"
    "实习,论文,开题,答辩,毕业,学位,文凭,证书,"
    "校园,教室,操场,图书馆,食堂,宿舍,实验室"
)

# Emotions / psychology / abstract
_ZH_EMOTION = (
    "高兴,快乐,幸福,满意,开心,愉快,兴奋,激动,"
    "感动,欣慰,自豪,骄傲,乐观,热情,积极,温暖,"
    "悲伤,难过,痛苦,伤心,失望,沮丧,焦虑,紧张,"
    "担心,害怕,恐惧,惊慌,绝望,无奈,烦恼,郁闷,"
    "生气,愤怒,恼火,暴躁,冲动,嫉妒,仇恨,厌恶,"
    "轻蔑,鄙视,冷漠,孤独,寂寞,空虚,迷茫,困惑,"
    "惊讶,好奇,怀疑,犹豫,矛盾,纠结,挣扎,彷徨,"
    "同情,怜悯,感恩,敬佩,崇拜,羡慕,嫉妒,思念,"
    "留恋,怀念,回忆,遗憾,后悔,内疚,羞愧,尴尬,"
    "勇气,信心,决心,耐心,恒心,毅力,意志,信念"
)

# Sports / entertainment / culture
_ZH_SPORTS = (
    "足球,篮球,排球,乒乓球,羽毛球,网球,棒球,"
    "高尔夫,田径,游泳,跳水,体操,举重,拳击,"
    "跆拳道,柔道,击剑,射击,射箭,马术,滑冰,"
    "滑雪,冲浪,攀岩,登山,跑步,竞走,跳远,跳高,"
    "铅球,铁饼,标枪,接力,马拉松,冠军,亚军,季军,"
    "金牌,银牌,铜牌,奖牌,世锦赛,奥运会,世界杯,"
    "联赛,锦标赛,淘汰赛,决赛,半决赛,教练,裁判,"
    "运动员,选手,队员,队长,主力,替补,阵容,战术,"
    "进攻,防守,得分,犯规,罚球,任意球,角球,点球,"
    "电影,电视剧,综艺,动画,纪录片,相声,小品,"
    "话剧,歌剧,舞蹈,芭蕾,交响乐,民乐,摇滚乐,"
    "流行乐,古典,现代,钢琴,吉他,小提琴,二胡"
)

# Politics / law / military
_ZH_POLITICS = (
    "政府,国会,议会,法院,检察院,公安局,派出所,"
    "消防队,海关,税务局,民政局,人社局,住建局,"
    "交通局,环保局,卫生局,教育局,财政局,审计局,"
    "监察委,纪委,政法委,宣传部,组织部,统战部,"
    "总统,主席,总理,部长,省长,市长,县长,区长,"
    "书记,委员,代表,顾问,秘书,参谋,司令,军长,"
    "师长,旅长,团长,营长,连长,排长,班长,战士,"
    "士兵,军官,将军,元帅,海军,陆军,空军,导弹,"
    "坦克,大炮,步枪,手枪,子弹,炸弹,地雷,鱼雷,"
    "雷达,卫星,火箭,航天,核武器,生化武器,防御,"
    "宪法,刑法,民法,商法,行政法,劳动法,合同法,"
    "婚姻法,继承法,专利法,商标法,著作权,知识产权"
)

# Time expressions
_ZH_TIME = (
    "今天,昨天,明天,前天,后天,上午,下午,早上,"
    "中午,晚上,凌晨,半夜,黎明,黄昏,傍晚,清晨,"
    "周一,周二,周三,周四,周五,周六,周日,星期,"
    "今年,去年,明年,前年,后年,本月,上月,下月,"
    "本周,上周,下周,本季,上季,下季,春天,夏天,"
    "秋天,冬天,春季,夏季,秋季,冬季,元旦,春节,"
    "清明,端午,中秋,国庆,除夕,元宵,七夕,重阳,"
    "节日,假日,工作日,休息日,纪念日,生日,周年,"
    "世纪,年代,时期,时代,早期,中期,晚期,初期,"
    "以前,以后,之前,之后,期间,当中,同时,刚才,"
    "现在,目前,当前,如今,最近,近来,近期,当时"
)

# Idioms and 4-char expressions
_ZH_IDIOM = (
    "一帆风顺,万事如意,心想事成,前程似锦,"
    "马到成功,事半功倍,全力以赴,脚踏实地,"
    "实事求是,与时俱进,自力更生,艰苦奋斗,"
    "团结协作,开拓创新,锐意进取,勇往直前,"
    "百折不挠,坚持不懈,持之以恒,循序渐进,"
    "因地制宜,因材施教,量力而行,适可而止,"
    "未雨绸缪,防患未然,居安思危,有备无患,"
    "相辅相成,相得益彰,取长补短,优势互补,"
    "博大精深,源远流长,丰富多彩,多姿多彩,"
    "异曲同工,殊途同归,大同小异,截然不同,"
    "日新月异,突飞猛进,蒸蒸日上,蓬勃发展,"
    "任重道远,责无旁贷,义不容辞,当仁不让,"
    "不可或缺,至关重要,举足轻重,不可忽视,"
    "放眼未来,着眼长远,立足当前,面向未来"
)

# Family / relationships / society
_ZH_FAMILY = (
    "父亲,母亲,爸爸,妈妈,爷爷,奶奶,外公,外婆,"
    "哥哥,姐姐,弟弟,妹妹,叔叔,阿姨,舅舅,姑姑,"
    "伯伯,婶婶,表哥,表姐,表弟,表妹,堂哥,堂姐,"
    "丈夫,妻子,儿子,女儿,孙子,孙女,外孙,侄子,"
    "侄女,女婿,儿媳,岳父,岳母,公公,婆婆,亲戚,"
    "邻居,同学,同事,朋友,伙伴,搭档,师傅,弟子,"
    "恋爱,结婚,离婚,订婚,求婚,婚礼,婚姻,夫妻,"
    "情侣,闺蜜,兄弟,姐妹,长辈,晚辈,同辈,后辈"
)

# Colors / shapes / positions
_ZH_DESCRIBE = (
    "红色,橙色,黄色,绿色,蓝色,紫色,黑色,白色,"
    "灰色,棕色,粉色,金色,银色,透明,深色,浅色,"
    "圆形,方形,三角形,长方形,椭圆形,菱形,梯形,"
    "正方形,球形,柱形,锥形,扇形,弧形,螺旋形,"
    "上面,下面,前面,后面,左边,右边,里面,外面,"
    "旁边,中间,对面,附近,周围,远处,近处,深处,"
    "顶部,底部,侧面,正面,背面,表面,内部,外部"
)

# Architecture / rooms / places
_ZH_PLACES = (
    "客厅,卧室,厨房,卫生间,阳台,书房,餐厅,"
    "地下室,走廊,楼梯,电梯,大厅,门厅,玄关,"
    "车库,仓库,储藏室,会议室,办公楼,教学楼,"
    "宿舍楼,图书馆,体育馆,游泳池,运动场,礼堂,"
    "医院,诊所,药店,超市,商场,百货,便利店,"
    "菜市场,批发市场,银行,邮局,派出所,消防站,"
    "加油站,充电站,公园,广场,花园,动物园,植物园,"
    "博物馆,美术馆,音乐厅,剧院,电影院,歌厅"
)

# Supplementary common words
_ZH_SUPP = (
    "方面,方案,背景,前景,全局,局部,细节,总体,"
    "整体,局面,形势,动态,走势,热点,焦点,亮点,"
    "难点,要点,重点,盲点,节点,拐点,支点,起点,"
    "落点,终点,观点,论点,焦点,冰点,沸点,零点,"
    "地点,景点,优点,缺点,特点,弱点,要点,卖点,"
    "买点,看点,痛点,爆点,燃点,闪点,盈亏,损益"
)


def _build_zh_dict() -> frozenset:
    """Build Chinese word dictionary."""
    parts = [
        _ZH_FUNC, _ZH_PRON, _ZH_VERB2, _ZH_NOUN2,
        _ZH_FORMAL, _ZH_ADJ, _ZH_ADV, _ZH_CONN,
        _ZH_COMPOUND, _ZH_SINGLE, _ZH_NUM,
        _ZH_EXTRA2, _ZH_EXTRA3,
        _ZH_HEALTH, _ZH_NATURE, _ZH_FOOD,
        _ZH_OBJECTS, _ZH_TRANSPORT, _ZH_TECH,
        _ZH_EDU, _ZH_EMOTION, _ZH_SPORTS,
        _ZH_POLITICS, _ZH_TIME, _ZH_IDIOM,
        _ZH_FAMILY, _ZH_DESCRIBE, _ZH_PLACES,
        _ZH_SUPP,
    ]
    words: set[str] = set()
    for part in parts:
        for w in part.split(","):
            w = w.strip()
            if w:
                words.add(w)
    return frozenset(words)


ZH_DICT: frozenset = _build_zh_dict()


# ── Japanese data ──────────────────────────────────

# Particles (sorted longest-first for matching)
_JA_PARTICLES_RAW = (
    "に対して,によって,にとって,において,について,"
    "に関して,に基づいて,にわたって,をもって,"
    "として,ながら,ために,ばかり,くらい,ぐらい,"
    "から,まで,より,だけ,ほど,など,さえ,こそ,"
    "しか,でも,のに,のが,のは,のを,ので,のも,"
    "では,とは,には,かも,けど,って,は,が,を,"
    "に,で,へ,と,も,の,か,や,よ,ね,わ,さ,"
    "ぞ,ぜ,な,し"
)

JA_PARTICLES: list[str] = sorted(
    [p.strip() for p in _JA_PARTICLES_RAW.split(",")
     if p.strip()],
    key=len,
    reverse=True,
)

# Common compound kanji words (not to split)
_JA_KANJI_COMPOUNDS_RAW = (
    "東京,日本,世界,社会,経済,政治,文化,教育,"
    "科学,技術,環境,情報,問題,方法,結果,理由,"
    "目的,関係,意味,価値,重要,必要,可能,特別,"
    "一般,基本,最新,現在,将来,過去,研究,開発,"
    "生産,建設,利用,管理,説明,表現,議論,分析,"
    "調査,計画,実行,実現,確認,評価,判断,理解,"
    "提供,改善,対応,参加,協力,支援,保護,維持,"
    "促進,推進,向上,強化,発展,変化,影響,効果,"
    "状況,条件,構造,機能,制度,組織,活動,事業,"
    "運動,作業,作品,製品,商品,食品,材料,資料,"
    "新聞,雑誌,記事,番組,映画,音楽,美術,写真,"
    "絵画,彫刻,建築,設計,工事,工場,企業,会社,"
    "銀行,病院,学校,大学,政府,議会,裁判,法律,"
    "規則,規定,基準,標準,方針,目標,成果,業績,"
    "能力,資格,経験,知識,技能,才能,努力,成功,"
    "失敗,安全,危険,事故,災害,被害,復旧,復興,"
    "改革,革命,戦争,平和,外交,貿易,輸出,輸入,"
    "投資,消費,収入,支出,利益,損失,市場,競争,"
    "独占,自由,平等,権利,義務,責任,国民,住民,"
    "市民,選挙,投票,代表,委員,議員,大臣,首相,"
    "大統領,交通,通信,運輸,放送,出版,広告,宣伝,"
    "報道,取材,会議,会談,交渉,契約,条約,協定,"
    "合意,決定,決議,承認,許可,申請,届出,届け,"
    "登録,届出,届け,届く,届ける,届け出,手続,"
    "手続き,手配,準備,用意,対策,措置,処理,"
    "処分,監督,監視,検査,審査,試験,実験,観察,"
    "測定,記録,統計,集計,予算,決算,会計,財政,"
    "金融,保険,年金,福祉,医療,介護,看護,治療,"
    "予防,健康,体力,精神,意識,感覚,感情,思考,"
    "記憶,想像,創造,発明,発見,証明,理論,原理,"
    "法則,定理,公式,計算,数学,物理,化学,生物,"
    "地理,歴史,哲学,論理,倫理,道徳,宗教,信仰,"
    "伝統,習慣,風俗,作法,礼儀,挨拶,会話,議論,"
    "演説,講演,授業,講義,指導,教授,教師,教員,"
    "生徒,学生,児童,園児,卒業,入学,入社,退職,"
    "就職,転職,出勤,退勤,出張,旅行,観光,散歩,"
    "運転,操作,製造,加工,修理,修繕,改修,改築,"
    "増築,新築,解体,撤去,設置,設立,創立,創業,"
    "開業,閉店,開店,営業,販売,購入,注文,配送,"
    "届け出,届け先,届け物,届ける,届く,届出,"
    "自然,天気,天候,気候,気温,湿度,風速,降水"
)

JA_COMPOUNDS: frozenset = frozenset(
    w.strip()
    for w in _JA_KANJI_COMPOUNDS_RAW.split(",")
    if w.strip()
)

# ── Korean data ────────────────────────────────────

# Particles sorted longest-first
_KO_PARTICLES_RAW = (
    "에게서,이라도,으로서,으로써,에서는,에게는,"
    "이라는,이라고,으로는,에서의,까지는,부터는,"
    "에서,에게,한테,까지,부터,보다,처럼,같이,"
    "마다,밖에,대로,조차,나마,이나,이든,이란,"
    "이라,으로,에는,에도,과는,와는,만은,도는,"
    "은,는,이,가,을,를,에,로,과,와,의,도,"
    "만,나,든,야,서,며"
)

KO_PARTICLES: list[str] = sorted(
    [p.strip() for p in _KO_PARTICLES_RAW.split(",")
     if p.strip()],
    key=len,
    reverse=True,
)


# ── Helper predicates ─────────────────────────────

def _is_cjk_char(ch: str) -> bool:
    """Return True if ch is a CJK ideograph."""
    cp = ord(ch)
    return (
        (0x4E00 <= cp <= 0x9FFF)
        or (0x3400 <= cp <= 0x4DBF)
        or (0x20000 <= cp <= 0x2A6DF)
        or (0x2A700 <= cp <= 0x2B73F)
        or (0x2B740 <= cp <= 0x2B81F)
        or (0x2B820 <= cp <= 0x2CEAF)
        or (0xF900 <= cp <= 0xFAFF)
        or (0x2F800 <= cp <= 0x2FA1F)
    )


def _is_hiragana(ch: str) -> bool:
    cp = ord(ch)
    return 0x3040 <= cp <= 0x309F


def _is_katakana(ch: str) -> bool:
    cp = ord(ch)
    return (
        (0x30A0 <= cp <= 0x30FF)
        or (0x31F0 <= cp <= 0x31FF)
        or (0xFF65 <= cp <= 0xFF9F)
    )


def _is_hangul(ch: str) -> bool:
    cp = ord(ch)
    return (
        (0xAC00 <= cp <= 0xD7AF)
        or (0x1100 <= cp <= 0x11FF)
        or (0x3130 <= cp <= 0x318F)
        or (0xA960 <= cp <= 0xA97F)
        or (0xD7B0 <= cp <= 0xD7FF)
    )


def _is_ascii_word(ch: str) -> bool:
    """ASCII letter, digit, or underscore."""
    return ch.isascii() and (
        ch.isalpha() or ch.isdigit() or ch == "_"
    )


# ── Chinese segmenter (BiMM) ──────────────────────

def _fmm(text: str, dic: frozenset,
         max_len: int) -> list[str]:
    """Forward Maximum Matching."""
    result: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        matched = text[i]
        for end in range(
            min(i + max_len, n), i + 1, -1
        ):
            candidate = text[i:end]
            if candidate in dic:
                matched = candidate
                break
        result.append(matched)
        i += len(matched)
    return result


def _bmm(text: str, dic: frozenset,
         max_len: int) -> list[str]:
    """Backward Maximum Matching."""
    result: list[str] = []
    n = len(text)
    i = n
    while i > 0:
        matched = text[i - 1]
        for start in range(
            max(i - max_len, 0), i - 1
        ):
            candidate = text[start:i]
            if candidate in dic:
                matched = candidate
                break
        result.append(matched)
        i -= len(matched)
    result.reverse()
    return result


def _count_singles(words: list[str]) -> int:
    """Count single-character words."""
    return sum(1 for w in words if len(w) == 1)


def _zh_segment(text: str) -> list[str]:
    """Segment Chinese text using BiMM."""
    fwd = _fmm(text, ZH_DICT, _ZH_MAX_WORD)
    bwd = _bmm(text, ZH_DICT, _ZH_MAX_WORD)
    if fwd == bwd:
        return fwd
    # Prefer fewer total words, then fewer singles
    if len(fwd) != len(bwd):
        return fwd if len(fwd) < len(bwd) else bwd
    fs = _count_singles(fwd)
    bs = _count_singles(bwd)
    return bwd if bs < fs else fwd


# ── Japanese segmenter (char-type) ────────────────

_JA_CHAR_TYPES = {
    "hiragana": 1,
    "katakana": 2,
    "kanji": 3,
    "ascii": 4,
    "other": 0,
}


def _ja_char_type(ch: str) -> int:
    """Classify a Japanese character."""
    if _is_hiragana(ch):
        return _JA_CHAR_TYPES["hiragana"]
    if _is_katakana(ch):
        return _JA_CHAR_TYPES["katakana"]
    if _is_cjk_char(ch):
        return _JA_CHAR_TYPES["kanji"]
    if _is_ascii_word(ch):
        return _JA_CHAR_TYPES["ascii"]
    return _JA_CHAR_TYPES["other"]


def _ja_try_compound(text: str, pos: int) -> str | None:
    """Try to match a known compound at pos."""
    max_c = min(len(text), pos + 8)
    for end in range(max_c, pos + 1, -1):
        sub = text[pos:end]
        if sub in JA_COMPOUNDS:
            return sub
    return None


def _ja_split_particles(
    tokens: list[str],
) -> list[str]:
    """Split trailing particles from tokens."""
    result: list[str] = []
    for tok in tokens:
        if len(tok) <= 1:
            result.append(tok)
            continue
        # Only split hiragana suffixes from kanji
        has_kanji = any(_is_cjk_char(c) for c in tok)
        if not has_kanji:
            result.append(tok)
            continue
        # Find where kanji ends
        ki = len(tok)
        for idx in range(len(tok) - 1, -1, -1):
            if _is_cjk_char(tok[idx]):
                ki = idx + 1
                break
        if ki >= len(tok):
            result.append(tok)
            continue
        tail = tok[ki:]
        head = tok[:ki]
        # Try to match particles in tail
        split_parts: list[str] = []
        ti = 0
        while ti < len(tail):
            matched = False
            for p in JA_PARTICLES:
                if tail[ti:].startswith(p):
                    split_parts.append(p)
                    ti += len(p)
                    matched = True
                    break
            if not matched:
                split_parts.append(tail[ti])
                ti += 1
        result.append(head)
        result.extend(split_parts)
    return result


def _ja_segment(text: str) -> list[str]:
    """Segment Japanese text by char-type."""
    if not text:
        return []
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        # Try compound kanji match
        if _is_cjk_char(ch):
            comp = _ja_try_compound(text, i)
            if comp:
                tokens.append(comp)
                i += len(comp)
                continue
        ctype = _ja_char_type(ch)
        if ctype == _JA_CHAR_TYPES["other"]:
            tokens.append(ch)
            i += 1
            continue
        # Collect same-type run
        j = i + 1
        while j < n:
            ntype = _ja_char_type(text[j])
            if ntype != ctype:
                # kanji followed by hiragana stays
                if (
                    ctype == _JA_CHAR_TYPES["kanji"]
                    and ntype
                    == _JA_CHAR_TYPES["hiragana"]
                ):
                    j += 1
                    continue
                break
            j += 1
        tokens.append(text[i:j])
        i = j
    # Split off particles
    tokens = _ja_split_particles(tokens)
    return tokens


# ── Korean segmenter ──────────────────────────────

def _ko_strip_particles(
    word: str,
) -> list[str]:
    """Strip Korean particles from end of word."""
    if not word:
        return []
    for p in KO_PARTICLES:
        if len(p) >= len(word):
            continue
        if word.endswith(p):
            stem = word[: len(word) - len(p)]
            if stem:
                return [stem, p]
    return [word]


def _ko_segment(text: str) -> list[str]:
    """Segment Korean text (space + particles)."""
    parts = text.split(" ")
    result: list[str] = []
    for idx, part in enumerate(parts):
        if not part:
            if idx < len(parts) - 1:
                result.append(" ")
            continue
        # Separate hangul runs from non-hangul
        runs = _split_mixed(part, _is_hangul)
        for run_text, is_hangul_run in runs:
            if is_hangul_run:
                stripped = _ko_strip_particles(
                    run_text
                )
                result.extend(stripped)
            else:
                result.append(run_text)
        if idx < len(parts) - 1:
            result.append(" ")
    return result


def _split_mixed(
    text: str, pred
) -> list[tuple[str, bool]]:
    """Split text into runs of pred-True / False."""
    if not text:
        return []
    runs: list[tuple[str, bool]] = []
    cur = text[0]
    cur_match = pred(text[0])
    for ch in text[1:]:
        m = pred(ch)
        if m == cur_match:
            cur += ch
        else:
            runs.append((cur, cur_match))
            cur = ch
            cur_match = m
    runs.append((cur, cur_match))
    return runs


# ── Mixed-script segmenter ────────────────────────

def _char_script(ch: str) -> str:
    """Determine script category of a character."""
    if ch.isspace():
        return "ws"
    if _is_hangul(ch):
        return "ko"
    if _is_hiragana(ch) or _is_katakana(ch):
        return "ja"
    if _is_cjk_char(ch):
        return "cjk"
    if _is_ascii_word(ch):
        return "ascii"
    cat = unicodedata.category(ch)
    if cat.startswith("P") or cat.startswith("S"):
        return "punct"
    return "other"


def _segment_mixed(
    text: str, lang: str
) -> list[str]:
    """Segment mixed-script text, dispatching."""
    if not text:
        return []
    # Split into script-homogeneous runs
    runs: list[tuple[str, str]] = []
    cur = text[0]
    cs = _char_script(text[0])
    for ch in text[1:]:
        s = _char_script(ch)
        if s == cs:
            cur += ch
        else:
            runs.append((cur, cs))
            cur = ch
            cs = s
    runs.append((cur, cs))

    result: list[str] = []
    for run_text, script in runs:
        if script == "ws":
            result.append(run_text)
        elif script == "ko":
            result.extend(_ko_segment(run_text))
        elif script == "ja":
            result.extend(_ja_segment(run_text))
        elif script == "cjk":
            if lang == "ja":
                result.extend(
                    _ja_segment(run_text)
                )
            elif lang == "ko":
                result.append(run_text)
            else:
                result.extend(
                    _zh_segment(run_text)
                )
        elif script == "ascii":
            result.append(run_text)
        else:
            result.append(run_text)
    return result


# ── Public API ─────────────────────────────────────

class CJKSegmenter:
    """CJK word segmenter.

    Supports Chinese (zh), Japanese (ja),
    and Korean (ko). No external dependencies.

    Parameters
    ----------
    lang : str
        Language code: "zh", "ja", or "ko".
    """

    __slots__ = ("lang",)

    def __init__(self, lang: str = "zh") -> None:
        lang = lang.lower().strip()
        if lang not in ("zh", "ja", "ko"):
            raise ValueError(
                f"Unsupported language: {lang!r}."
                " Use 'zh', 'ja', or 'ko'."
            )
        self.lang = lang

    def segment(self, text: str) -> list[str]:
        """Segment text into words.

        Returns a list of word strings.
        Whitespace tokens are preserved.
        """
        if not text:
            return []
        return _segment_mixed(text, self.lang)

    def segment_with_positions(
        self, text: str
    ) -> list[tuple[str, int, int]]:
        """Segment with character positions.

        Returns list of (word, start, end) tuples
        where start is inclusive and end exclusive.
        """
        words = self.segment(text)
        result: list[tuple[str, int, int]] = []
        pos = 0
        for w in words:
            end = pos + len(w)
            result.append((w, pos, end))
            pos = end
        return result

    def tokenize(self, text: str) -> list[str]:
        """Segment and strip whitespace tokens.

        Like segment() but removes whitespace-only
        tokens from the result.
        """
        return [
            w for w in self.segment(text)
            if not w.isspace()
        ]


def segment_cjk(
    text: str, lang: str = "zh"
) -> list[str]:
    """Convenience function: segment CJK text.

    Parameters
    ----------
    text : str
        Input text to segment.
    lang : str
        Language code ("zh", "ja", "ko").

    Returns
    -------
    list[str]
        Segmented word list.
    """
    return CJKSegmenter(lang).segment(text)


def is_cjk_text(text: str) -> bool:
    """Return True if text contains CJK chars.

    Checks for Chinese ideographs, Japanese kana,
    or Korean hangul characters.
    """
    for ch in text:
        if (
            _is_cjk_char(ch)
            or _is_hiragana(ch)
            or _is_katakana(ch)
            or _is_hangul(ch)
        ):
            return True
    return False


def detect_cjk_lang(
    text: str,
) -> str | None:
    """Detect CJK language from text content.

    Returns "zh", "ja", "ko", or None.

    Heuristic priority:
    - Any hangul -> "ko"
    - Any hiragana/katakana -> "ja"
    - CJK ideographs only -> "zh"
    """
    has_cjk = False
    has_hangul = False
    has_kana = False
    for ch in text:
        if _is_hangul(ch):
            has_hangul = True
        elif _is_hiragana(ch) or _is_katakana(ch):
            has_kana = True
        elif _is_cjk_char(ch):
            has_cjk = True
    if has_hangul:
        return "ko"
    if has_kana:
        return "ja"
    if has_cjk:
        return "zh"
    return None
