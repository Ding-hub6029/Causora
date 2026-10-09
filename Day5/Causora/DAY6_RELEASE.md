# Causora — Day6 统一冻结与交接

文件夹/ZIP 按用户要求命名为 Day3。本包实际内容是 Day6，依据 Causora v3.0 原始规格第22–25页。不要将文件名误读为任务日期。

网站：https://causora-one.vercel.app/
后端：https://causora-api.onrender.com
代码：https://github.com/Ding-hub6029/Causora

## 统一口径

- 所有包使用同一份 Causora 源码和 freeze.json。不得把三份项目分别覆盖部署。
- 104周 / 24个月。ds-001。seed 1042026。formula tco-v1。已审核的合成样例数据。
- 当前公开运行与 Golden 快照为1000次 Monte Carlo。10000次是本次本地性能/跨seed验证，不宣称公开站已切到10000次。
- D0保留A。D1保留A最低份额并引入B。D2退出A并支付25000美元退出费。D2只有B，不称为供应商多元化。
- 合同通知60天、续约24个月、最低份额60%、涨价14%。需求下降15%到22100，A最低承诺仍为15600，须区分锁定预测与滚动需求。
- 代码计算数字。OpenRouter提供定性角色评审、Critic及简报。校验/模板填充不等于模型内部思维可见。不能保证每次内容完全相同。
- LIVE、真实快照的CACHED、Day2静态MOCK必须分开。缓存只读不发AI请求。旧评审不能套用新simulation/dataVersion/scenario/requestId。
- Approve/Reject只记录本浏览器选择，不是供应商承诺、法律签署或服务器永久审批。

## 本次检查

24项后端HTTP/门控测试通过。125项AI与评估测试通过。前端62项测试及3项静态部署测试通过，并通过typecheck、lint、静态/live生产构建。原始日志见 evidence。
Golden真实快照通过生产校验器，4条Evidence齐备，修改场景会拒绝。真实AI调用凭据见脱敏provider-receipts.json。离线14案例单独标为TEST_FIXTURE_ONLY，不冒充实测模型质量。
新增公开入口单进程并发1、启动间隔15秒。429保留矩阵，拒绝请求不进入模型。异常释放并发槽。Render入口强制启用。多worker扩容前必须升级分布式限流。
同seed的10000次数学预览重复一致。三seed缺货概率最大差0.78个百分点，低于2pp。九格Golden成本分项全部合计一致。本地10000次单次基准约0.51秒，Windows峰值RSS未测得，不写虚构内存数字。

## 冻结规则

只修可复现bug。修改数字、合同解释、prompt、模型、超时或身份字段须重跑相关检查并重导出Golden。源码哈希清单供核对，不包含node_modules、venv、密钥、数据库地址或预算私有文件。
启动依照Causora/DEPLOYMENT_GUIDE.md。老师密钥仅由后台环境注入。源码包不携带秘密。免费数据库当前到期日为2026-11-09，提交后长期运行须另做维护。

## 未冒充完成的验收事项

原规格G6要求8个Hard Blockers全绿，现有证据不足以宣布全绿：最终2–4分钟视频尚未录制/上传，Devpost正式提交与成员账号核验属于Day7。陌生设备/真正无痕的本轮复验尚未记录。已提供逐项步骤与成稿。只有Wang Hao的一份真实用户反馈，不能编造2–3名用户或替Deng签署。
<45秒真实AI、10轮完整在线成功、独立未见Critic recall>=80%尚未建立合格测量证据，作为Strong Target明确保留，不把离线14/14写成真实召回率。保留历史失败记录。录屏前必须实际打开一次全链路。
