import { useEffect, useState } from "react";
import {
  Card, Form, Input, InputNumber, Button, Collapse, Space, message, Spin, Divider, Tag, Alert, Result,
} from "antd";
import { SaveOutlined, ApiOutlined, LinkOutlined, CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined } from "@ant-design/icons";
import { apiGet, apiPost, ApiError } from "../api/client";

interface SettingItem {
  key: string;
  value: string;
  masked: boolean;
}

interface SettingsGroup {
  title: string;
  icon: React.ReactNode;
  description: string;
  fields: { key: string; label: string; type: "text" | "password" | "number"; placeholder?: string }[];
}

const GROUPS: SettingsGroup[] = [
  {
    title: "TAPD 集成",
    icon: <ApiOutlined />,
    description: "TAPD 需求管理平台连接配置",
    fields: [
      { key: "TAPD_API_URL", label: "API 地址", type: "text", placeholder: "https://api.tapd.cn" },
      { key: "TAPD_API_TOKEN", label: "Access Token", type: "password", placeholder: "在 TAPD 个人设置 → API 中生成" },
      { key: "TAPD_WORKSPACE_ID", label: "工作区 ID", type: "text", placeholder: "项目 URL 中的数字，如 tapd.cn/tapd_fe/12345678/..." },
      { key: "TAPD_SYNC_INTERVAL", label: "同步间隔（秒）", type: "number", placeholder: "300" },
    ],
  },
  {
    title: "GitLab",
    icon: <LinkOutlined />,
    description: "GitLab 代码仓库配置",
    fields: [
      { key: "GITLAB_URL", label: "GitLab 地址", type: "text", placeholder: "https://gitlab.example.com" },
      { key: "GITLAB_TOKEN", label: "Access Token", type: "password", placeholder: "GitLab Personal Access Token" },
      { key: "GITLAB_DEFAULT_BASE_PATH", label: "仓库基础路径", type: "text", placeholder: "/data/repos" },
    ],
  },
  {
    title: "Claude Code",
    icon: <ApiOutlined />,
    description: "Claude Code CLI 集成配置",
    fields: [
      { key: "CLAUDE_CODE_TIMEOUT", label: "超时时间（秒）", type: "number", placeholder: "600" },
    ],
  },
  {
    title: "CI/CD",
    icon: <LinkOutlined />,
    description: "持续集成/部署配置",
    fields: [
      { key: "CICD_PROVIDER", label: "CI/CD 提供商", type: "text", placeholder: "gitlab" },
      { key: "CICD_TRIGGER_URL", label: "触发 URL", type: "text", placeholder: "Pipeline trigger URL" },
      { key: "CICD_TRIGGER_TOKEN", label: "Trigger Token", type: "password", placeholder: "Pipeline trigger token" },
    ],
  },
  {
    title: "LLM API Keys",
    icon: <ApiOutlined />,
    description: "大语言模型 API 密钥配置",
    fields: [
      { key: "OPENAI_API_KEY", label: "OpenAI API Key", type: "password", placeholder: "sk-..." },
      { key: "OPENAI_API_BASE", label: "OpenAI API Base", type: "text", placeholder: "https://api.openai.com/v1" },
      { key: "ANTHROPIC_API_KEY", label: "Anthropic API Key", type: "password", placeholder: "sk-ant-..." },
      { key: "GOOGLE_API_KEY", label: "Google API Key", type: "password", placeholder: "AIza..." },
      { key: "DEEPSEEK_API_KEY", label: "DeepSeek API Key", type: "password", placeholder: "sk-..." },
      { key: "MINIMAX_API_KEY", label: "MiniMax API Key", type: "password", placeholder: "eyJ..." },
    ],
  },
];

export default function SettingsPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    status: "idle" | "testing" | "success" | "error";
    message?: string;
    detail?: string;
    sampleCount?: number;
    workspaceName?: string;
  }>({ status: "idle" });
  const [originalValues, setOriginalValues] = useState<Record<string, string>>({});

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const items: SettingItem[] = await apiGet("/settings");
      const values: Record<string, string> = {};
      for (const item of items) {
        // 敏感字段不填入表单（避免脱敏值被当作真实值），留空由 placeholder 提示
        if (item.masked && item.value) {
          values[item.key] = "";
        } else {
          values[item.key] = item.value;
        }
      }
      setOriginalValues(values);
      form.setFieldsValue(values);
    } catch (err) {
      message.error("加载配置失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      // 只提交有变化的字段；敏感字段为空时跳过（保留已有值）
      const sensitiveKeys = new Set(GROUPS.flatMap(g => g.fields).filter(f => f.type === "password").map(f => f.key));
      const updates: { key: string; value: string }[] = [];
      for (const [key, value] of Object.entries(values)) {
        const strVal = String(value ?? "").trim();
        // 敏感字段：空值跳过，不覆盖后端已有值
        if (sensitiveKeys.has(key) && !strVal) continue;
        if (strVal !== originalValues[key]) {
          updates.push({ key, value: strVal });
        }
      }

      if (updates.length === 0) {
        message.info("配置无变更");
        setSaving(false);
        return;
      }

      await apiPost("/settings", { settings: updates });
      message.success("配置已保存，部分设置需要重启服务后生效");
      loadSettings();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        message.error(err.message);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleTestTAPD = async () => {
    setTesting(true);
    setTestResult({ status: "testing" });
    try {
      // 直接把当前表单的 TAPD 值传给后端测试，不依赖先保存
      const values = form.getFieldsValue();
      const api_token = String(values.TAPD_API_TOKEN || "").trim();
      const workspace_id = String(values.TAPD_WORKSPACE_ID || "").trim();
      const api_url = String(values.TAPD_API_URL || "").trim();

      const result = await apiPost<{ connected: boolean; sample_count: number; workspace_name: string }>("/settings/test-tapd", {
        api_token,
        workspace_id,
        api_url,
      });
      if (result.connected) {
        setTestResult({
          status: "success",
          message: "TAPD 连接成功",
          detail: result.workspace_name
            ? `已连接到工作区「${result.workspace_name}」，可正常获取需求数据`
            : "API 认证通过，当前工作区可获取需求数据",
          sampleCount: result.sample_count,
          workspaceName: result.workspace_name,
        });
      } else {
        setTestResult({
          status: "error",
          message: "连接返回但状态异常",
          detail: "请检查工作区 ID 是否正确",
        });
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setTestResult({
          status: "error",
          message: err.message,
        });
      }
    } finally {
      setTesting(false);
    }
  };

  // 检测哪些配置组有值
  const getGroupStatus = (group: SettingsGroup) => {
    const filled = group.fields.filter(f => originalValues[f.key] && originalValues[f.key] !== "").length;
    if (filled === 0) return <Tag color="default">未配置</Tag>;
    if (filled === group.fields.length) return <Tag color="green">已配置</Tag>;
    return <Tag color="orange">部分配置</Tag>;
  };

  if (loading) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>;
  }

  return (
    <Card
      title="系统设置"
      extra={
        <Space>
          <Button
            onClick={handleTestTAPD}
            loading={testing}
            icon={<ApiOutlined />}
          >
            测试 TAPD 连接
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
          >
            保存配置
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical" size="middle">
        <Collapse
          defaultActiveKey={["0"]}
          items={GROUPS.map((group, idx) => ({
            key: String(idx),
            label: (
              <Space>
                {group.icon}
                <span style={{ fontWeight: 500 }}>{group.title}</span>
                {getGroupStatus(group)}
              </Space>
            ),
            children: (
              <>
                <div style={{ color: "#999", marginBottom: 16, fontSize: 13 }}>
                  {group.description}
                </div>
                {group.fields.map((field) => (
                  <Form.Item
                    key={field.key}
                    name={field.key}
                    label={field.label}
                  >
                    {field.type === "password" ? (
                      <Input.Password
                        placeholder={field.placeholder}
                        autoComplete="new-password"
                      />
                    ) : field.type === "number" ? (
                      <InputNumber
                        placeholder={field.placeholder}
                        style={{ width: "100%" }}
                      />
                    ) : (
                      <Input placeholder={field.placeholder} />
                    )}
                  </Form.Item>
                ))}
                <Divider style={{ margin: "8px 0 16px" }} />
              </>
            ),
          }))}
        />
      </Form>

      {/* TAPD 连接测试结果 */}
      {testResult.status !== "idle" && (
        <Card
          size="small"
          style={{ marginTop: 16, borderRadius: 8 }}
          bodyStyle={{ padding: "16px 24px" }}
        >
          {testResult.status === "testing" && (
            <Space>
              <LoadingOutlined style={{ fontSize: 18, color: "#1890ff" }} />
              <span style={{ color: "#666" }}>正在连接 TAPD 并验证凭据...</span>
            </Space>
          )}
          {testResult.status === "success" && (
            <Result
              status="success"
              title={testResult.message}
              subTitle={testResult.detail}
              extra={
                <Space>
                  {testResult.sampleCount !== undefined && (
                    <Tag color="blue" style={{ fontSize: 14, padding: "4px 12px" }}>
                      查询到 {testResult.sampleCount} 条需求数据
                    </Tag>
                  )}
                  {testResult.workspaceName && (
                    <Tag color="green" style={{ fontSize: 14, padding: "4px 12px" }}>
                      {testResult.workspaceName}
                    </Tag>
                  )}
                </Space>
              }
            />
          )}
          {testResult.status === "error" && (
            <Result
              status="error"
              title="TAPD 连接失败"
              subTitle={testResult.message}
            />
          )}
        </Card>
      )}

      <div style={{ marginTop: 24, padding: "12px 16px", background: "#fafafa", borderRadius: 8 }}>
        <strong>提示：</strong>
        <ul style={{ margin: "8px 0 0", paddingLeft: 20, color: "#666" }}>
          <li>TAPD / GitLab 等集成配置保存后立即生效（同步操作时使用新配置）</li>
          <li>LLM API Keys 修改后需要重启后端服务才能生效</li>
          <li>密码类字段以脱敏形式显示，如需修改请重新输入完整值</li>
        </ul>
      </div>
    </Card>
  );
}
