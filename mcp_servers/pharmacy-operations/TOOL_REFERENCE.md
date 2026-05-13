# MCP Tool Reference

这份文档面向两类人：

- 设计题目的人：核对工具职责是不是清楚
- 跑评测的人：确认模型拿到的工具到底会返回什么

## 会话前提

- 外层 harness 先调用内部方法 `session/create`
- 模型随后通过 `tools/list` 看到 15 个业务工具
- 之后所有业务工具都必须带 `session_id`

## 公共返回约定

所有工具返回都会尽量包含：

- `session_id`
- `question_id`
- `remaining_budget`

此外还会带一个主结果对象：

- 查询类：`items` / `drug_base_info` / `inventory_record` / `batch_record` / `clinical_rule` / `reimbursement_rule`
- 记录类：`record`
- 库存更新类：`inventory_update`
- 导出类：`export`

## 读类工具

### `search_drug_catalog`

作用：
- 第一层粗召回候选药
- 不保证唯一命中

典型输入：

```json
{
  "session_id": "sess_xxx",
  "query": "急性扁桃腺炎",
  "limit": 5
}
```

典型返回：

```json
{
  "items": [
    {
      "drug_id": "super_000063",
      "master_id": "master_00063",
      "question_id": "v5_001",
      "source_excel": "v5_001_ward_dispensing.xlsx",
      "source_row_index": "63",
      "通用名": "胆木注射液",
      "品牌名": "海南",
      "剂型": "注射剂",
      "规格": "每只装 2 ml（含胆木提取物 6 mg）",
      "单位": "支",
      "医保类型": "非医保"
    }
  ],
  "remaining_budget": 9
}
```

### `get_drug_base_info`

作用：
- 用 `drug_id` 读取主数据
- 适合在候选消歧时用

返回重点：
- `drug_base_info`
- 通用名、品牌名、剂型、规格、包装规格

### `get_inventory_record`

作用：
- 读库存快照
- 看是否低于警戒线

返回重点：
- `inventory_record`
- `库存量`
- `会话内库存量`
- `单位`
- `补货警戒线`
- `库位`
- `单位价格(元)`

### `get_batch_record`

作用：
- 读批号和效期
- 适合 FEFO、交班、近效期提醒

返回重点：
- `batch_record`
- `批号`
- `效期至`

### `get_clinical_rule`

作用：
- 读说明书/药学规则

返回重点：
- `clinical_rule`
- `适应症`
- `用法用量`
- `禁忌`
- `儿童用药`
- `老年用药`
- `孕妇用药`
- `不良反应`
- `医保类型`

### `get_reimbursement_rule`

作用：
- 读医保和支付相关判断依据

返回重点：
- `reimbursement_rule`
- `医保类型`
- `适应症`
- `禁忌`
- `儿童用药`
- `老年用药`
- `孕妇用药`

## 写类工具

### `create_dispense_record`

作用：
- 新建发药/摆药记录

必填输入：
- `session_id`
- `drug_id`
- `quantity`

返回重点：
- `record_id`
- `record_type = dispense_record`
- `status = created`
- `quantity`
- `unit`
- `batch_no`

### `create_inventory_warning`

作用：
- 新建库存预警

必填输入：
- `session_id`
- `drug_id`
- `warning_type`

返回重点：
- `record_id`
- `record_type = inventory_warning`
- `warning_type`
- `severity`

### `create_audit_note`

作用：
- 新建审方/药学审核意见

必填输入：
- `session_id`
- `decision`

返回重点：
- `record_id`
- `record_type = audit_note`
- `decision`
- `reason`
- `note`

### `create_insurance_intercept`

作用：
- 新建医保拦截记录

必填输入：
- `session_id`
- `decision`
- `reason`

返回重点：
- `record_id`
- `record_type = insurance_intercept`
- `decision`
- `reason`

### `create_handoff_note`

作用：
- 新建交班记录

必填输入：
- `session_id`
- `note`

返回重点：
- `record_id`
- `record_type = handoff_note`
- `shift`
- `note`

## 更新类工具

### `update_inventory_balance`

作用：
- 改会话内库存

必填输入：
- `session_id`
- `drug_id`
- `mode`
- `quantity`

返回重点：
- `before`
- `after`
- `unit`

支持模式：
- `decrease`
- `increase`
- `set`

### `update_record_status`

作用：
- 改记录状态

必填输入：
- `session_id`
- `record_id`
- `status`

返回重点：
- 更新后的完整记录对象

### `update_audit_decision`

作用：
- 改 `audit_note` 或 `insurance_intercept` 的结论

必填输入：
- `session_id`
- `record_id`
- `decision`

返回重点：
- 更新后的完整记录对象
- 如果传了 `reason` / `note`，会写回记录

## 导出类工具

### `export_operation_log`

作用：
- 导出本次会话全部结果

必填输入：
- `session_id`

返回重点：
- `export_path`
- `records`
- `inventory_state`
- `events`
- `remaining_budget`

## 实测状态

可以直接运行：

```bash
python3 test_visible_tools.py
```

当前这份脚本已经验证：
- 15 个模型可见工具都可正常返回
- 内部工具 `create_session` / `list_question_profiles` 不会暴露给模型
