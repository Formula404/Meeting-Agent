markdown消息
目前仅支持markdown语法的子集
微工作台（原企业号）不支持展示markdown消息
请求示例：

{
   "touser" : "UserID1|UserID2|UserID3",
   "toparty" : "PartyID1|PartyID2",
   "totag" : "TagID1 | TagID2",
   "msgtype": "markdown",
   "agentid" : 1,
   "markdown": {
        "content": "您的会议室已经预定，稍后会同步到`邮箱`  \n>**事项详情**  \n>事　项：<font color=\"info\">开会</font>  \n>组织者：@miglioguan  \n>参与者：@miglioguan、@kunliu、@jamdeezhou、@kanexiong、@kisonwang  \n>  \n>会议室：<font color=\"info\">广州TIT 1楼 301</font>  \n>日　期：<font color=\"warning\">2018年5月18日</font>  \n>时　间：<font color=\"comment\">上午9:00-11:00</font>  \n>  \n>请准时参加会议。  \n>  \n>如需修改会议信息，请点击：[修改会议信息](https://work.weixin.qq.com)"
   },
   "enable_duplicate_check": 0,
   "duplicate_check_interval": 1800
}

参数说明：

参数	是否必须	说明
touser	否	成员ID列表（消息接收者，多个接收者用‘|’分隔，最多支持1000个）。特殊情况：指定为@all，则向关注该企业应用的全部成员发送
toparty	否	部门ID列表，多个接收者用‘|’分隔，最多支持100个。当touser为@all时忽略本参数
totag	否	标签ID列表，多个接收者用‘|’分隔，最多支持100个。当touser为@all时忽略本参数
msgtype	是	消息类型，此时固定为：markdown
agentid	是	企业应用的id，整型。企业内部开发，可在应用的设置页面查看；第三方服务商，可通过接口 获取企业授权信息 获取该参数值
content	是	markdown内容，最长不超过2048个字节，必须是utf8编码
enable_duplicate_check	否	表示是否开启重复消息检查，0表示否，1表示是，默认0
duplicate_check_interval	否	表示是否重复消息检查的时间间隔，默认1800s，最大不超过4小时

支持的markdown语法
目前应用消息中支持的markdown语法是如下的子集：

标题 （支持1至6级标题，注意#与文字中间要有空格）
# 标题一
## 标题二
### 标题三
#### 标题四
##### 标题五
###### 标题六
加粗
**bold**
链接
[这是一个链接](http://work.weixin.qq.com/api/doc)
行内代码段（暂不支持跨行）
`code`
引用
> 引用文字
字体颜色(只支持3种内置颜色)
<font color="info">绿色</font>
<font color="comment">灰色</font>
<font color="warning">橙红色</font>