#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema清理和验证工具
"""
from typing import Any, Dict, List

def is_empty_value(value: Any) -> bool:
    """检查值是否为空"""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def deep_clean(value: Any) -> Any:
    """深度清理值，移除空值"""
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in value.items():
            vv = deep_clean(v)
            if is_empty_value(vv):
                continue
            cleaned[k] = vv
        return cleaned
    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            ii = deep_clean(item)
            if is_empty_value(ii):
                continue
            cleaned_list.append(ii)
        return cleaned_list
    if isinstance(value, str):
        return value.strip()
    return value


def infer_type_for_property(prop_name: str) -> str:
    """根据属性名推断类型"""
    name = prop_name.lower()
    if name in ("url", "uri", "href", "link"):
        return "string"
    if name in ("headers", "options", "params", "payload", "data"):
        return "object"
    return "string"


def ensure_property_schema(name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """确保属性schema的完整性"""
    prop = dict(schema) if isinstance(schema, dict) else {}
    
    # 对于空dict，先不清理，保留以便后续处理
    if not prop:
        prop = {}
    
    # 必填：type & description
    if "type" not in prop or not isinstance(prop.get("type"), str) or not prop["type"].strip():
        prop["type"] = infer_type_for_property(name)
    if "description" not in prop or not isinstance(prop.get("description"), str) or not prop["description"].strip():
        prop["description"] = f"{name} parameter"

    # 特殊处理 headers
    if name.lower() == "headers":
        prop["type"] = "object"
        headers_props = prop.get("properties")
        if not isinstance(headers_props, dict):
            headers_props = {}
        headers_props = deep_clean(headers_props)
        if not headers_props:
            headers_props = {
                "user-agent": {
                    "type": "string",
                    "description": "User-Agent header for the request",
                }
            }
        else:
            # 清理并保证每个 header 的子属性都具备 type/description
            fixed_headers: Dict[str, Any] = {}
            for hk, hv in headers_props.items():
                sub = deep_clean(hv if isinstance(hv, dict) else {})
                if "type" not in sub or not isinstance(sub.get("type"), str) or not sub["type"].strip():
                    sub["type"] = "string"
                if "description" not in sub or not isinstance(sub.get("description"), str) or not sub["description"].strip():
                    sub["description"] = f"{hk} header"
                fixed_headers[hk] = sub
            headers_props = fixed_headers
        prop["properties"] = headers_props
        # 处理 required 空数组
        if isinstance(prop.get("required"), list):
            req = [r for r in prop["required"] if isinstance(r, str) and r in headers_props]
            if req:
                prop["required"] = req
            else:
                prop.pop("required", None)
        # additionalProperties 若为空 dict，删除
        if isinstance(prop.get("additionalProperties"), dict) and len(prop["additionalProperties"]) == 0:
            prop.pop("additionalProperties", None)

    return prop


def sanitize_json_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """清理和修正JSON Schema"""
    s = dict(schema) if isinstance(schema, dict) else {}

    # 如果存在 properties，则顶层应为 object
    if "properties" in s and not isinstance(s.get("type"), str):
        s["type"] = "object"

    # 修正 $schema
    if "$schema" in s and not isinstance(s["$schema"], str):
        s.pop("$schema", None)
    if "$schema" not in s:
        s["$schema"] = "http://json-schema.org/draft-07/schema#"

    properties = s.get("properties")
    if isinstance(properties, dict):
        fixed_props: Dict[str, Any] = {}
        for name, subschema in properties.items():
            fixed_props[name] = ensure_property_schema(name, subschema if isinstance(subschema, dict) else {})
        s["properties"] = fixed_props

    # required：去掉不存在的属性，且不允许为空列表
    if isinstance(s.get("required"), list):
        if isinstance(properties, dict):
            req = [r for r in s["required"] if isinstance(r, str) and r in properties]
        else:
            req = []
        if req:
            s["required"] = req
        else:
            s.pop("required", None)

    # additionalProperties：空 dict 视为无效，删除
    if isinstance(s.get("additionalProperties"), dict) and len(s["additionalProperties"]) == 0:
        s.pop("additionalProperties", None)

    return s