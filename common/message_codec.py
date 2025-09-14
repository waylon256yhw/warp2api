#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server Message Data 编解码工具
用于处理 Base64URL 编码的 protobuf 消息
"""
import base64
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None  # type: ignore


class MessageCodec:
    """Server Message Data 编解码器"""
    
    @staticmethod
    def b64url_decode_padded(s: str) -> bytes:
        """Base64URL解码（带填充）"""
        t = s.replace("-", "+").replace("_", "/")
        pad = (-len(t)) % 4
        if pad:
            t += "=" * pad
        return base64.b64decode(t)
    
    @staticmethod
    def b64url_encode_nopad(b: bytes) -> str:
        """Base64URL编码（无填充）"""
        return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")
    
    @staticmethod
    def read_varint(buf: bytes, i: int) -> Tuple[int, int]:
        """读取varint格式的整数"""
        shift = 0
        val = 0
        while i < len(buf):
            b = buf[i]
            i += 1
            val |= (b & 0x7F) << shift
            if not (b & 0x80):
                return val, i
            shift += 7
            if shift > 63:
                break
        raise ValueError("invalid varint")
    
    @staticmethod
    def write_varint(v: int) -> bytes:
        """写入varint格式的整数"""
        out = bytearray()
        vv = int(v)
        while True:
            to_write = vv & 0x7F
            vv >>= 7
            if vv:
                out.append(to_write | 0x80)
            else:
                out.append(to_write)
                break
        return bytes(out)
    
    @classmethod
    def make_key(cls, field_no: int, wire_type: int) -> bytes:
        """创建protobuf字段键"""
        return cls.write_varint((field_no << 3) | wire_type)
    
    @classmethod
    def decode_timestamp(cls, buf: bytes) -> Tuple[Optional[int], Optional[int]]:
        """解码google.protobuf.Timestamp"""
        i = 0
        seconds: Optional[int] = None
        nanos: Optional[int] = None
        while i < len(buf):
            key, i = cls.read_varint(buf, i)
            field_no = key >> 3
            wt = key & 0x07
            if wt == 0:  # varint
                val, i = cls.read_varint(buf, i)
                if field_no == 1:
                    seconds = int(val)
                elif field_no == 2:
                    nanos = int(val)
            elif wt == 2:  # length-delimited
                ln, i2 = cls.read_varint(buf, i)
                i = i2 + ln
            elif wt == 1:
                i += 8
            elif wt == 5:
                i += 4
            else:
                break
        return seconds, nanos
    
    @classmethod
    def encode_timestamp(cls, seconds: Optional[int], nanos: Optional[int]) -> bytes:
        """编码google.protobuf.Timestamp"""
        parts = bytearray()
        if seconds is not None:
            parts += cls.make_key(1, 0)  # field 1, varint
            parts += cls.write_varint(int(seconds))
        if nanos is not None:
            parts += cls.make_key(2, 0)  # field 2, varint
            parts += cls.write_varint(int(nanos))
        return bytes(parts)
    
    @classmethod
    def decode_server_message_data(cls, b64url: str) -> Dict:
        """解码 Base64URL 的 server_message_data"""
        try:
            raw = cls.b64url_decode_padded(b64url)
        except Exception as e:
            return {"error": f"base64url decode failed: {e}", "raw_b64url": b64url}
        
        i = 0
        uuid: Optional[str] = None
        seconds: Optional[int] = None
        nanos: Optional[int] = None
        
        while i < len(raw):
            key, i = cls.read_varint(raw, i)
            field_no = key >> 3
            wt = key & 0x07
            if wt == 2:  # length-delimited
                ln, i2 = cls.read_varint(raw, i)
                i = i2
                data = raw[i:i+ln]
                i += ln
                if field_no == 1:  # uuid string
                    try:
                        uuid = data.decode("utf-8")
                    except Exception:
                        uuid = None
                elif field_no == 3:  # google.protobuf.Timestamp
                    seconds, nanos = cls.decode_timestamp(data)
            elif wt == 0:  # varint
                _, i = cls.read_varint(raw, i)
            elif wt == 1:
                i += 8
            elif wt == 5:
                i += 4
            else:
                break
        
        out: Dict[str, Any] = {}
        if uuid is not None:
            out["uuid"] = uuid
        if seconds is not None:
            out["seconds"] = seconds
        if nanos is not None:
            out["nanos"] = nanos
        return out
    
    @classmethod
    def encode_server_message_data(cls, uuid: str = None, seconds: int = None, nanos: int = None) -> str:
        """将 uuid/seconds/nanos 组合编码为 Base64URL 字符串"""
        parts = bytearray()
        if uuid:
            b = uuid.encode("utf-8")
            parts += cls.make_key(1, 2)  # field 1, length-delimited
            parts += cls.write_varint(len(b))
            parts += b
        
        if seconds is not None or nanos is not None:
            ts = cls.encode_timestamp(seconds, nanos)
            parts += cls.make_key(3, 2)  # field 3, length-delimited
            parts += cls.write_varint(len(ts))
            parts += ts
        
        return cls.b64url_encode_nopad(bytes(parts))


# 为了向后兼容，提供简单的函数接口
decode_server_message_data = MessageCodec.decode_server_message_data
encode_server_message_data = MessageCodec.encode_server_message_data