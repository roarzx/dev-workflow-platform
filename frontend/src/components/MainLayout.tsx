import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, Typography } from "antd";
import {
  UnorderedListOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  SettingOutlined,
} from "@ant-design/icons";

const { Sider, Content, Header } = Layout;

const menuItems = [
  { key: "/tasks", icon: <UnorderedListOutlined />, label: "需求看板" },
  { key: "/tasks?status=open", icon: <SyncOutlined />, label: "开发中" },
  { key: "/tasks?status=completed", icon: <CheckCircleOutlined />, label: "已完成" },
  { key: "/settings", icon: <SettingOutlined />, label: "设置" },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  // 匹配菜单高亮
  const selectedKey = menuItems.find((item) => {
    const menuPath = item.key.split("?")[0]; // 去掉 query string
    return location.pathname === menuPath;
  })?.key || "/tasks";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          background: "#fff",
          padding: "0 24px",
          borderBottom: "1px solid #f0f0f0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Typography.Title level={4} style={{ margin: 0 }}>
          Dev Workflow
        </Typography.Title>
        <Typography.Text type="secondary">开发者</Typography.Text>
      </Header>
      <Layout>
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          theme="light"
          style={{ borderRight: "1px solid #f0f0f0" }}
        >
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={menuItems}
            onClick={handleMenuClick}
            style={{ border: "none", marginTop: 8 }}
          />
        </Sider>
        <Content style={{ margin: 24, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
