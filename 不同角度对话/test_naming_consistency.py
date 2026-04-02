import unittest
from importlib import util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "main.py"
MODULE_SPEC = util.spec_from_file_location("dynamic_cognitive_orchestrator_main", MODULE_PATH)
main = util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC and MODULE_SPEC.loader
MODULE_SPEC.loader.exec_module(main)


def make_request() -> main.AnalyzeRequest:
    return main.AnalyzeRequest(topic="AI 会替代大部分白领工作吗？", agent_count="4")


def make_casting_payload() -> dict:
    return {
        "issue_type": "复合型",
        "topic_deconstruction": {
            "surface_conflict": "大家在争 AI 到底是机会还是威胁",
            "real_dispute": "谁会失去议价权，谁能先拿到效率红利",
            "key_variables": ["岗位标准化程度", "行业景气度", "个人迁移能力"],
            "loud_but_minor": "短视频里的极端成功学故事",
            "silent_but_powerful": "企业真实的成本压力",
        },
        "conflict_axes": ["利益分配", "风险承担", "时间尺度"],
        "agents": [
            {
                "id": "agent_1",
                "display_name": "小红",
                "alias": "转行焦虑白领",
                "age": "29岁",
                "identity": "一线城市互联网运营",
                "core_interest": "保住收入并找到新机会",
                "main_fear": "技能过时后被边缘化",
                "info_type": "一线工具使用反馈",
                "dimensions": ["职业迁移", "技能替代"],
                "blind_spot": "低估组织惯性",
                "why_selected": "她代表最典型的焦虑白领",
                "voice_profile": {
                    "sentence_length_tendency": "短句偏多，先把态度亮出来",
                    "abstraction_preference": "偏具体，只说自己碰到的事",
                    "expression_habits": ["喜欢先讲眼前结论", "常把风险说得很直白"],
                    "emotion_intensity": "中高，压着焦虑说",
                    "reasoning_moves": ["喜欢举身边小例子", "喜欢直接下判断"],
                },
            },
            {
                "id": "agent_2",
                "code_name": "王二",
                "age": "36岁",
                "identity": "二线城市小老板",
                "core_interest": "控制用人成本",
                "main_fear": "投入新工具却没有回报",
                "info_type": "经营现金流数据",
                "dimensions": ["现金流", "决策节奏"],
                "blind_spot": "容易高估短期 ROI",
                "why_selected": "他能代表务实经营者",
            },
            {
                "id": "agent_3",
                "age": "45岁",
                "identity": "传统企业中层",
                "core_interest": "维持团队稳定",
                "main_fear": "流程改造引发失控",
                "info_type": "组织执行摩擦",
                "dimensions": ["组织治理", "内部协同"],
                "blind_spot": "对新工具学习意愿偏低",
                "why_selected": "他代表制度惯性一侧",
            },
            {
                "id": "agent_4",
                "display_name": "阿梅",
                "alias": "精打细算家长",
                "age": "38岁",
                "identity": "有孩子的双职工家长",
                "core_interest": "家庭收入和时间都别失控",
                "main_fear": "盲目换赛道把家庭拖进风险",
                "info_type": "家庭支出和教育压力",
                "dimensions": ["家庭决策", "风险承受"],
                "blind_spot": "可能低估新城市长期机会",
                "why_selected": "她能带来家庭约束视角",
            },
        ],
    }


class NamingConsistencyTests(unittest.TestCase):
    def test_global_system_prompt_includes_quality_guardrails_and_runtime(self):
        req = make_request()
        system_prompt = main.build_system_prompt(req.model_dump())

        self.assertIn("深度分档规格", system_prompt)
        self.assertIn("红线一：语言阶层锁", system_prompt)
        self.assertIn("红线四：制度角色兜底", system_prompt)
        self.assertIn("圆桌激辩", system_prompt)
        self.assertIn("800-1200", system_prompt)
        self.assertIn("20000", system_prompt)
        self.assertIn("说实话", system_prompt)
        self.assertIn("## 话题", system_prompt)
        self.assertIn("AI 会替代大部分白领工作吗？", system_prompt)
        self.assertIn("## Agent 数量", system_prompt)
        self.assertIn("4", system_prompt)

    def test_normalize_casting_unifies_visible_name_fields(self):
        casting = main.normalize_casting(make_casting_payload(), make_request())
        agents = casting["agents"]

        self.assertEqual([agent["id"] for agent in agents], ["agent_1", "agent_2", "agent_3", "agent_4"])
        self.assertEqual(agents[0]["display_name"], "小红")
        self.assertEqual(agents[0]["alias"], "转行焦虑白领")
        self.assertEqual(agents[0]["voice_profile"]["sentence_length_tendency"], "短句偏多，先把态度亮出来")
        self.assertEqual(agents[1]["display_name"], "王二")
        self.assertEqual(agents[1]["alias"], "现金流")
        self.assertEqual(agents[2]["display_name"], "阿杰")
        self.assertEqual(agents[3]["display_name"], "阿梅")
        self.assertNotEqual(agents[1]["voice_profile"]["sentence_length_tendency"], agents[2]["voice_profile"]["sentence_length_tendency"])
        self.assertNotEqual(agents[1]["voice_profile"]["reasoning_moves"], agents[2]["voice_profile"]["reasoning_moves"])

        for agent in agents:
            self.assertIn("display_name", agent)
            self.assertIn("alias", agent)
            self.assertIn("voice_profile", agent)
            self.assertNotIn("code_name", agent)
            self.assertNotIn("role_tag", agent)

    def test_prompts_use_display_name_as_primary_reference(self):
        req = make_request()
        casting = main.normalize_casting(make_casting_payload(), req)
        agent_outputs = [{**agent, "monologue": f"{agent['display_name']} 的独白"} for agent in casting["agents"]]

        director_prompt = main.build_director_prompt(req, casting, agent_outputs)
        agent_prompt = main.build_agent_prompt(req, casting, casting["agents"][0])

        self.assertIn("- 小红｜补充标签：转行焦虑白领", director_prompt)
        self.assertIn("## 小红", director_prompt)
        self.assertNotIn("## 转行焦虑白领", director_prompt)
        self.assertIn("必须优先使用阵容里给出的 `display_name`", director_prompt)
        self.assertIn("- 你的主显示名：小红", agent_prompt)
        self.assertIn("- 你的补充标签：转行焦虑白领", agent_prompt)
        self.assertIn("## 你的说话习惯", agent_prompt)
        self.assertIn("- 句子节奏：短句偏多，先把态度亮出来", agent_prompt)
        self.assertIn("喜欢举身边小例子；喜欢直接下判断", agent_prompt)
        self.assertIn("Ultra：800 到 1200 字", agent_prompt)
        self.assertIn("尽量不要用太通用的开场口头禅", agent_prompt)

    def test_roundtable_prompt_only_for_pro_and_ultra(self):
        pro_req = main.AnalyzeRequest(topic="AI 会替代大部分白领工作吗？", agent_count="4", depth="pro")
        standard_req = main.AnalyzeRequest(topic="AI 会替代大部分白领工作吗？", agent_count="4", depth="standard")
        casting = main.normalize_casting(make_casting_payload(), pro_req)
        agent_outputs = [{**agent, "monologue": f"{agent['display_name']} 的暗房独白"} for agent in casting["agents"]]

        roundtable_prompt = main.build_roundtable_prompt(pro_req, casting, agent_outputs)

        self.assertTrue(main.should_include_roundtable(pro_req))
        self.assertFalse(main.should_include_roundtable(standard_req))
        self.assertIn("【圆桌激辩】", roundtable_prompt)
        self.assertIn("每位 Agent 都必须对前面至少 1 个具体观点做", roundtable_prompt)
        self.assertIn("冲突张力最大的两方先碰撞", roundtable_prompt)
        self.assertIn("A 的论点被 B 精确反驳", roundtable_prompt)
        self.assertIn("意外共识", roundtable_prompt)
        self.assertIn("3 到 4 位冲突最尖锐的角色上桌", roundtable_prompt)
        self.assertIn("2 到 3 轮交锋", roundtable_prompt)
        self.assertIn("说实话", roundtable_prompt)

    def test_agent_count_rules_follow_auto_4_to_8_and_manual_10(self):
        base_payload = make_casting_payload()
        extra_agents = []
        for index in range(5, 11):
            extra_agents.append(
                {
                    "id": f"agent_{index}",
                    "display_name": f"角色{index}",
                    "alias": f"补充标签{index}",
                    "age": f"{25 + index}岁",
                    "identity": f"测试身份{index}",
                    "core_interest": f"测试利益{index}",
                    "main_fear": f"测试风险{index}",
                    "info_type": f"测试信息{index}",
                    "dimensions": [f"维度{index}A", f"维度{index}B"],
                    "blind_spot": f"测试盲点{index}",
                    "why_selected": f"测试原因{index}",
                }
            )

        payload_with_ten = {**base_payload, "agents": [*base_payload["agents"], *extra_agents]}

        auto_result = main.normalize_casting(payload_with_ten, main.AnalyzeRequest(topic="测试", agent_count="auto"))
        manual_result = main.normalize_casting(payload_with_ten, main.AnalyzeRequest(topic="测试", agent_count="10"))

        self.assertEqual(len(auto_result["agents"]), 8)
        self.assertEqual(len(manual_result["agents"]), 10)


if __name__ == "__main__":
    unittest.main()
