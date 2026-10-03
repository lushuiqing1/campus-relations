# 二创来源与改写记录

整理日期：2026-10-03。

## 固定上游

项目：[shengjidaguai-china/goutoujunshi](https://github.com/shengjidaguai-china/goutoujunshi)。本次核对 `HEAD` 后固定 commit `6db7354a4002dc7c448a9c87ffdad8132570c9d3`，不将后续上游更新自动混入此版本。

| 核对文件 | 固定来源 | 本地快照 SHA-256 |
|---|---|---|
| SKILL.md | [源文件](https://github.com/shengjidaguai-china/goutoujunshi/blob/6db7354a4002dc7c448a9c87ffdad8132570c9d3/SKILL.md) | `825edd66bed33ce514c12d0cd3f2f002417c7aa357b58a6aae658cad26f6e083` |
| agents/openai.yaml | [源文件](https://github.com/shengjidaguai-china/goutoujunshi/blob/6db7354a4002dc7c448a9c87ffdad8132570c9d3/agents/openai.yaml) | `ee51fe0998e7785b61268ac0f3e76699507efd0bdb63cc4ca735c686db531d06` |
| LICENSE | [源文件](https://github.com/shengjidaguai-china/goutoujunshi/blob/6db7354a4002dc7c448a9c87ffdad8132570c9d3/LICENSE) | `f336b7d0101d93b47ec1964aaf3c4ab12dc582638be9501fc883801a51ed0367` |
| scripts/validate_skill.py | [源文件](https://github.com/shengjidaguai-china/goutoujunshi/blob/6db7354a4002dc7c448a9c87ffdad8132570c9d3/scripts/validate_skill.py) | `49813893d512e68ca486dac91a32279213ad92735aa034f5c2bb3e9807e5804b` |
| scripts/memory_store.py | [源文件](https://github.com/shengjidaguai-china/goutoujunshi/blob/6db7354a4002dc7c448a9c87ffdad8132570c9d3/scripts/memory_store.py) | `dde4c38488d232a35e2bff6897885edb9df097f92ac12ee38c3a79e9778a5ca5` |

上游完整快照留在开发资料区，未作为校园版运行内容分发。

## 继承与重写

继承上游的共享工作流：承接情绪、区分事实与未知、给首选建议、生成可发送话术、根据反馈调整；以及核心入口和按需参考文件的结构。

校园版入口按大学生目的重写：没有首次 MBTI／综合评分问卷，不将主动追求与吸引力排序作为师生或同学关系默认决策。评判改为清晰沟通、可靠履约、公平、适当互助、边界和持续共处。

v0.1 的三个 practical 文件、论文转述、测试题和示例均为本项目编写。它们借鉴公开研究所讨论的情境，不复制第三方对话或全文，不把学校个案安排当作统一校规。

界面名称、内部 ID 和默认调用统一为 `campus-relations`。校验器与安装器为本项目实现，上游验证器硬编码的原版标识和恋爱材料要求不再使用。

上游记忆脚本使用固定 `goutoujunshi` 存储目录和 `GOUTOUJUNSHI_MEMORY_DIR` 环境变量，不能仅靠改技能文件名获得隔离。校园版 v0.1、v0.2 均不包含这段代码或持久化关系档案；后续版本若加入记忆，另行设计独立存储与明确同意。

## v0.2 再融合

用户要求将校园版与已安装的原版融合，并选择师生、同学关系和校园恋爱两种方向。本次使用同一固定上游，未将其整套行为入口并排加载。

| 融合模块 | 上游来源 | 校园化处理 |
|---|---|---|
| [话术编排](../references/practical/conversation-playbook.md) | 实战话术编排器、聊天化被动为主动、巧妙接话 | 单轮主动作、三层按需组合、自然口吻、真实反馈分支、逐轮演练 |
| [聊天分析](../references/practical/chat-analysis.md) | SKILL.md、ChatLab 适配 | 说话人映射、分段事件、约定兑现、不同角色，实际可用时才接工具 |
| [社交校准](../references/practical/social-calibration.md) | 场景感、自然流与知识 20 | 状态容纳、现场取材、开放假设、结构／素材／表达排错 |
| [校园恋爱](../references/practical/campus-romance.md) | 主动表达、投入失衡、话术编排、MBTI 与同意资料 | 同辈心动与邀请、含糊反馈、明确拒绝、共处与退出；师生评价权力另行考虑 |

各文件提供固定版本原文链接或来源目录说明，具体校园例子重新编写。恋爱策略属于经验与设计建议，不伪装成已有大学生研究验证的效力。

原版的强制 MBTI／评分建档、按性别加码主动、婚姻家庭全套资料和持久记忆没有引入本次校园融合范围。技能仍独立安装，调用保持 `$campus-relations`。

## v0.2.1 中文表达整合

用户要求将已安装的 humanizer-zh 融入校园 Skill。本次依据本地 2026-09-23 修订，而非假定 GitHub 当前版本与本地文件相同。

- 本地入口：`~/.codex/skills/humanizer-zh/SKILL.md`。
- 入口 SHA-256：`ccfe3ac1c2ec9f92d8512e3d600b3f7245c8f33e8814fd4b00569061e060c9c7`。
- 该修订注明参考 [blader/humanizer v3.0.0](https://github.com/blader/humanizer/blob/v3.0.0/SKILL.md)、[Humanizer-zh PR 39](https://github.com/op7418/Humanizer-zh/pull/39) 及 [stop-slop](https://github.com/hardikpandya/stop-slop)。这些是本地文件记录的来源，本次没有重新核验或声称合并上述版本。
- 本地许可为 MIT，版权行是 `Copyright (c) 2026 歸藏`；已将该声明与完整许可保留在项目 [LICENSE](../LICENSE)。

整合内容是保留事实、确定程度、范围与条件，匹配对象和用户声音，只改实际表达问题，直接交付最终文本。入口提供共同规则，详细核对和两个原创例子放入[话术编排](../references/practical/conversation-playbook.md)。没有复制整个模式清单，不进行作者身份判断或检测器评分，不将独立 humanizer-zh 的绝对路径做成运行依赖。

新增示例均重新编写，旧版验证报告和原始回答不润色。明确调用的检查结果单独记录，不把 v0.2 的行为通过结果当成 v0.2.1 的新测结果。

## v0.2.2 连续对话与名称统一

在既有校园规则上补充当前聊天中的口吻偏好范围、草稿与真实反馈区分、用户纠正后的更新，以及明确倾诉和演练反馈时机。新增连续片段和闲聊示例为本项目原创，没有引入新的上游内容或依赖。对外展示名改为“校园关系军师”，调用名称仍为 `campus-relations`；上游与 humanizer-zh 的来源和许可继续保留。

这次不实现跨聊天记忆，不改变既有研究的适用范围。新验证使用逐条输入的连续对话，实际记录与历史单轮结果分开保存。

## 资料的许可边界

上游 MIT 原版权行与许可完整保留于 [LICENSE](../LICENSE)。校园版新增内容也采用 MIT；[NOTICE.md](../NOTICE.md)说明项目关系。

第三方资料只保留简短转述和链接。以 CMU 的 [教师自述](https://www.cmu.edu/teaching/designteach/teach/stories/cover.html) 为例，其页面许可为 CC BY-NC-SA 4.0，不因上游 MIT 获得全文分发授权。

论文的样本、方法、摘要或全文核验范围及勘误状态见[研究依据](../references/knowledge/evidence.md)。尚未复查成功的教育案例不作为已核证据，整个 Skill 的真实使用效果尚待学生反馈与独立评估。
完整检索记录保留于[资料索引](research-index.md)，该文件只随项目源码分发，不默认进入技能上下文。
