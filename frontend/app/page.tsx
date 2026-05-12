"use client";

import { LockKeyhole, LogIn, Plus, RefreshCw, Smartphone, WalletCards } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import {
  createDevice,
  createOrder,
  Device,
  listDevices,
  listOrders,
  login,
  mockPaymentCallback,
  Order
} from "../lib/api";

export default function HomePage() {
  const [token, setToken] = useState("");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("123456");
  const [devices, setDevices] = useState<Device[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [deviceSn, setDeviceSn] = useState("");
  const [deviceName, setDeviceName] = useState("");
  const [orderSn, setOrderSn] = useState("");
  const [amount, setAmount] = useState("1.00");
  const [callbackToken, setCallbackToken] = useState("replace-with-provider-secret");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const latestOrder = useMemo(() => orders[0], [orders]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    try {
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "操作失败");
    } finally {
      setBusy(false);
    }
  }

  async function refresh(nextToken = token) {
    if (!nextToken) return;
    const [deviceRows, orderRows] = await Promise.all([listDevices(nextToken), listOrders(nextToken)]);
    setDevices(deviceRows);
    setOrders(orderRows.sort((a, b) => b.id - a.id));
  }

  function handleLogin(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      const result = await login(username, password);
      setToken(result.access_token);
      await refresh(result.access_token);
      setMessage("已登录");
    });
  }

  function handleCreateDevice(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      await createDevice(token, { sn: deviceSn, name: deviceName || undefined });
      setDeviceSn("");
      setDeviceName("");
      await refresh();
    });
  }

  function handleCreateOrder(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      await createOrder(token, { device_sn: orderSn, amount });
      setOrderSn("");
      await refresh();
    });
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Distributed Unlock Console</p>
          <h1>订单支付开锁系统</h1>
        </div>
        <button className="iconButton" onClick={() => run(() => refresh())} disabled={!token || busy} title="刷新">
          <RefreshCw size={18} />
        </button>
      </section>

      <section className="grid">
        <form className="panel compact" onSubmit={handleLogin}>
          <h2><LogIn size={18} /> 登录</h2>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="用户名" />
          <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="密码" type="password" />
          <button disabled={busy}>登录并加载</button>
        </form>

        <form className="panel compact" onSubmit={handleCreateDevice}>
          <h2><Smartphone size={18} /> 设备</h2>
          <input value={deviceSn} onChange={(e) => setDeviceSn(e.target.value)} placeholder="设备 SN" />
          <input value={deviceName} onChange={(e) => setDeviceName(e.target.value)} placeholder="设备名称" />
          <button disabled={!token || busy}><Plus size={16} /> 添加设备</button>
        </form>

        <form className="panel compact" onSubmit={handleCreateOrder}>
          <h2><WalletCards size={18} /> 下单</h2>
          <input value={orderSn} onChange={(e) => setOrderSn(e.target.value)} placeholder="设备 SN" />
          <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="金额" />
          <button disabled={!token || busy}><LockKeyhole size={16} /> 创建订单</button>
        </form>
      </section>

      <section className="workspace">
        <div className="panel">
          <h2>设备列表</h2>
          <div className="table">
            {devices.map((device) => (
              <div className="row" key={device.id}>
                <strong>{device.sn}</strong>
                <span>{device.name || "未命名"}</span>
                <span className={`badge ${device.status}`}>{device.status}</span>
              </div>
            ))}
            {devices.length === 0 && <p className="empty">暂无设备</p>}
          </div>
        </div>

        <div className="panel">
          <h2>订单列表</h2>
          <div className="table">
            {orders.map((order) => (
              <div className="row" key={order.id}>
                <strong>#{order.id}</strong>
                <span>{order.amount} {order.currency}</span>
                <span>retry {order.retry_count}</span>
                <span className={`badge ${order.status}`}>{order.status}</span>
              </div>
            ))}
            {orders.length === 0 && <p className="empty">暂无订单</p>}
          </div>
        </div>
      </section>

      <section className="panel callback">
        <h2>支付回调预留</h2>
        <input value={callbackToken} onChange={(e) => setCallbackToken(e.target.value)} placeholder="回调 token" />
        <button
          disabled={!latestOrder || busy}
          onClick={() =>
            latestOrder &&
            run(async () => {
              await mockPaymentCallback({ order_id: latestOrder.id, token: callbackToken, provider: "manual" });
              await refresh();
            })
          }
        >
          模拟最近订单支付成功
        </button>
      </section>

      {message && <div className="toast">{message}</div>}
    </main>
  );
}
