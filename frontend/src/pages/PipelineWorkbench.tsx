import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Steps, Button, Input, Space, Typography, message, Spin, Divider, Tag,
} from "antd";
import { ArrowLeftOutlined, SendOutlined, CheckOutlined, RobotOutlined } from "@ant-design/icons";
import { apiGet, apiPost } from "../api/client";

const { TextArea } = Input;
const { Title, Text } = Typography;

interface Pipeline {
  id: number;
  task_id: number;
  status: string;
  branch: string | null;
  plan_result: string | null;
  code_commit: string | null;
  review_result: string | null;
  review_verdict: string | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
}

interface ChatMessage {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

const statusStepMap: Record<string, number> = {
  idle: 0,
  planning: 1,
  dispatching: 2,
  reviewing: 3,
  testing: 4,
  ready_to_submit: 4,
  completed: 5,
  failed: -1,
};

export default function PipelineWorkbench() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const pipelineId = Number(id);

  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchPipeline = useCallback(async () => {
    try {
      const data = await apiGet<Pipeline>(`/pipelines/${pipelineId}`);
      setPipeline(data);
    } catch {
      message.error("加载管线失败");
    } finally {
      setLoading(false);
    }
  }, [pipelineId]);

  useEffect(() => {
    fetchPipeline();
  }, [fetchPipeline]);

  const handleSend = async () => {
    if (!inputMessage.trim()) return;
    setSending(true);
    try {
      const result = await apiPost<{
        reply: string;
        status: string;
        message_id: number;
      }>(`/pipelines/${pipelineId}/chat`, { message: inputMessage });

      setMessages((prev) => [
        ...prev,
        { id: result.message_id - 1, role: "user", content: inputMessage, created_at: new Date().toISOString() },
        { id: result.message_id, role: "assistant", content: result.reply, created_at: new Date().toISOString() },
      ]);
      setInputMessage("");
    } catch (err) {
      message.error("发送失败");
    } finally {
      setSending(false);
    }
  };

  const handleConfirmPlan = async () => {
    try {
      await apiPost(`/pipelines/${pipelineId}/confirm-plan`, {
        plan_summary: "方案已确认",
      });
      message.success("方案已确认，代码生成中...");
      fetchPipeline();
    } catch (err) {
      message.error("确认方案失败");
    }
  };

  const currentStep = pipeline ? statusStepMap[pipeline.status] : 0;

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!pipeline) return null;

  return (
    <div>
      {/* 顶部信息 */}
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/tasks")}>
          返回看板
        </Button>
        <Title level={4} style={{ margin: 0 }}>
          管线 #{pipeline.id}
        </Title>
        <Tag color={pipeline.status === "failed" ? "red" : "blue"}>
          {pipeline.status}
        </Tag>
        {pipeline.branch && (
          <Text code>{pipeline.branch}</Text>
        )}
      </Space>

      {/* 状态进度条 */}
      <Card style={{ marginBottom: 16 }}>
        <Steps
          current={Math.max(currentStep, 0)}
          status={pipeline.status === "failed" ? "error" : "process"}
          items={[
            { title: "创建" },
            { title: "方案讨论" },
            { title: "代码生成" },
            { title: "代码审查" },
            { title: "部署测试" },
            { title: "提测完成" },
          ]}
        />
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* 左：AI 对话面板 */}
        <Card
          title={
            <Space>
              <RobotOutlined />
              <span>AI 方案讨论</span>
            </Space>
          }
          style={{ minHeight: 400 }}
        >
          {/* 对话消息 */}
          <div style={{ maxHeight: 300, overflowY: "auto", marginBottom: 16 }}>
            {messages.length === 0 && (
              <Text type="secondary" style={{ display: "block", textAlign: "center", padding: 40 }}>
                在此与 AI 讨论技术方案...
              </Text>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  textAlign: msg.role === "user" ? "right" : "left",
                  marginBottom: 12,
                }}
              >
                <Tag
                  color={msg.role === "user" ? "blue" : "green"}
                  style={{ marginBottom: 4 }}
                >
                  {msg.role === "user" ? "你" : "AI"}
                </Tag>
                <div
                  style={{
                    display: "inline-block",
                    maxWidth: "80%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    background: msg.role === "user" ? "#e6f4ff" : "#f6ffed",
                    textAlign: "left",
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}
          </div>

          <Divider />

          {/* 输入区 */}
          <Space.Compact style={{ width: "100%" }}>
            <TextArea
              rows={2}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="描述你的想法或问题..."
              disabled={pipeline.status !== "planning"}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={sending}
              disabled={pipeline.status !== "planning" || !inputMessage.trim()}
              style={{ height: "auto" }}
            >
              发送
            </Button>
          </Space.Compact>
        </Card>

        {/* 右：方案文档区 */}
        <Card title="方案文档" style={{ minHeight: 400 }}>
          {pipeline.plan_result ? (
            <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>
              {pipeline.plan_result}
            </pre>
          ) : (
            <Text type="secondary" style={{ display: "block", textAlign: "center", padding: 40 }}>
              确认方案后将在此展示最终方案...
            </Text>
          )}

          {pipeline.review_result && (
            <>
              <Divider>代码审查意见</Divider>
              <div>
                <Tag color={pipeline.review_verdict === "pass" ? "green" : "orange"}>
                  {pipeline.review_verdict}
                </Tag>
                <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>
                  {pipeline.review_result}
                </pre>
              </div>
            </>
          )}

          {pipeline.error_message && (
            <>
              <Divider>错误信息</Divider>
              <pre style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "#ff4d4f" }}>
                {pipeline.error_message}
              </pre>
            </>
          )}
        </Card>
      </div>

      {/* 底部操作栏 */}
      <Card style={{ marginTop: 16 }}>
        <Space size="middle">
          {pipeline.status === "planning" && (
            <Button type="primary" icon={<CheckOutlined />} onClick={handleConfirmPlan}>
              确认方案
            </Button>
          )}
          {pipeline.status === "reviewing" && (
            <>
              <Button onClick={() => message.info("Phase 3 实现")}>启动审查</Button>
              <Button type="primary" onClick={() => message.info("Phase 3 实现")}>部署测试</Button>
            </>
          )}
          {pipeline.status === "testing" && (
            <Button type="primary" onClick={() => message.info("Phase 3 实现")}>提测</Button>
          )}
          {pipeline.status === "failed" && (
            <Button onClick={() => message.info("Phase 3 实现")}>重试</Button>
          )}
        </Space>
      </Card>
    </div>
  );
}
