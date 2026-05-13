import { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Table, Button, Tag, Space, Select, message, Card, Tooltip,
} from "antd";
import { SyncOutlined } from "@ant-design/icons";
import { apiGet, apiPost, ApiError } from "../api/client";

interface Task {
  id: number;
  tapd_id: string;
  title: string;
  status: string;
  priority: string | null;
  tapd_url: string | null;
  synced_at: string;
}

interface PaginatedData {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

const statusColors: Record<string, string> = {
  open: "blue",
  progressing: "orange",
  done: "green",
  closed: "default",
};

const priorityLabels: Record<string, string> = {
  1: "P1-紧急",
  2: "P2-高",
  3: "P3-中",
  4: "P4-低",
};

export default function TaskBoard() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [data, setData] = useState<PaginatedData | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const statusFilter = searchParams.get("status") || undefined;

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        page: "1",
        page_size: "20",
      };
      if (statusFilter) params.status = statusFilter;
      const result = await apiGet<PaginatedData>("/tasks", params);
      setData(result);
    } catch (err) {
      message.error("加载需求列表失败");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const stats = await apiPost<{ created: number; updated: number; skipped: number }>("/tasks/sync");
      const parts: string[] = [];
      if (stats.created) parts.push(`新增 ${stats.created} 条`);
      if (stats.updated) parts.push(`更新 ${stats.updated} 条`);
      if (stats.skipped) parts.push(`跳过 ${stats.skipped} 条`);
      message.success(parts.length ? parts.join("，") : "同步完成，无变更");
      fetchTasks();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : "同步请求失败，请检查网络连接";
      message.error(msg);
    } finally {
      setSyncing(false);
    }
  };

  const handleStartDev = async (taskId: number) => {
    try {
      const pipeline = await apiPost<{ id: number }>("/pipelines", { task_id: taskId });
      message.success("管线已创建");
      navigate(`/pipeline/${pipeline.id}`);
    } catch (err) {
      message.error("创建管线失败");
    }
  };

  const columns = [
    {
      title: "TAPD ID",
      dataIndex: "tapd_id",
      width: 140,
      render: (id: string) => (
        <Tooltip title={`TAPD ${id}`}>
          <Tag>{id.slice(-6)}</Tag>
        </Tooltip>
      ),
    },
    {
      title: "需求标题",
      dataIndex: "title",
      ellipsis: true,
      render: (title: string) => (
        <span style={{ cursor: "pointer" }}>{title}</span>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (status: string) => (
        <Tag color={statusColors[status] || "default"}>{status}</Tag>
      ),
    },
    {
      title: "优先级",
      dataIndex: "priority",
      width: 90,
      render: (p: string | null) => (
        p ? <Tag color={p === "1" ? "red" : p === "2" ? "orange" : "blue"}>
          {priorityLabels[p] || `P${p}`}
        </Tag> : "-"
      ),
    },
    {
      title: "最后同步",
      dataIndex: "synced_at",
      width: 170,
      render: (t: string) => new Date(t).toLocaleString("zh-CN"),
    },
    {
      title: "操作",
      width: 140,
      render: (_: unknown, record: Task) => (
        <Space>
          <Button type="link" size="small" disabled={!record.tapd_url}>
            <a href={record.tapd_url || "#"} target="_blank" rel="noreferrer">
              TAPD
            </a>
          </Button>
          <Button
            type="primary"
            size="small"
            onClick={() => handleStartDev(record.id)}
          >
            开始开发
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="需求看板"
      extra={
        <Space>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            value={statusFilter || undefined}
            onChange={(val) => {
              if (val) setSearchParams({ status: val });
              else setSearchParams({});
            }}
            options={[
              { value: "open", label: "待处理" },
              { value: "progressing", label: "进行中" },
              { value: "done", label: "已完成" },
              { value: "closed", label: "已关闭" },
            ]}
          />
          <Button
            icon={<SyncOutlined spin={syncing} />}
            onClick={handleSync}
            loading={syncing}
          >
            同步 TAPD
          </Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={loading}
        pagination={{
          total: data?.total || 0,
          pageSize: data?.page_size || 20,
          showTotal: (t) => `共 ${t} 条`,
          showSizeChanger: false,
        }}
      />
    </Card>
  );
}
