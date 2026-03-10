import { useState, useEffect, useRef, useCallback } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

// ─── ASM1 simplified model (runs in browser) ───────────────────────────────
function asm1Step(state, inputs, dt_s) {
  const { S_s, S_NH, X_H, X_A, DO, MLSS } = state;
  const {
    Q_in = 25, S_s_in = 150, S_NH_in = 30,
    KLa = 6.0, DO_sat = 9.1, T = 22,
    Q_air = 5, D_PAC = 3, D_NaOH = 0.5
  } = inputs;

  const dt_h = dt_s / 3600;
  const V = 200;
  const HRT = V / Math.max(Q_in, 1);
  const tc = Math.pow(1.072, T - 20);

  // Process rates
  const mu_H = 6.0 * tc * (S_s / (20 + S_s)) * (DO / (0.2 + DO));
  const rho_1 = mu_H * X_H * 0.001;
  const b_H = 0.62 * tc;
  const rho_2 = b_H * X_H * 0.001;
  const mu_A = 0.8 * tc * (S_NH / (1.0 + S_NH)) * (DO / (0.4 + DO));
  const rho_3 = mu_A * X_A * 0.001;
  const b_A = 0.15 * tc;
  const rho_4 = b_A * X_A * 0.001;

  // KLa from air flow
  const KLa_actual = 0.08 * Math.pow(Math.max(Q_air, 0.1), 0.75);
  const OUR = ((1 - 0.67) / 0.67 * rho_1 + (4.57 - 0.24) / 0.24 * rho_3 + rho_2 + rho_4);

  // pH effect on coagulation (simplified turbidity model)
  const pH_eff = Math.exp(-Math.pow(7.2 - (7.0 + 0.1 * S_NH / 20), 2) / (2 * 0.64));
  const coag_removal = Math.min(1, D_PAC * 0.003 * pH_eff);

  const dS_s  = ((S_s_in - S_s) / HRT - rho_1 / 0.67) * dt_h;
  const dS_NH = ((S_NH_in - S_NH) / HRT - rho_3 / 0.24 + 0.07 * (rho_2 + rho_4)) * dt_h;
  const dX_H  = (-X_H / HRT + (rho_1 - rho_2) / 0.67 * 0.5) * dt_h;
  const dX_A  = (-X_A / HRT + (rho_3 - rho_4) * 2) * dt_h;
  const dDO   = (KLa_actual * (DO_sat - DO) - OUR + (0.5 - DO) / HRT) * dt_h;

  // Virtual sensor noise
  const noise = (std) => (Math.random() - 0.5) * 2 * std;

  const turbidity_raw = Math.max(0.1, S_s * 0.05 * (1 - coag_removal) + MLSS * 0.001);

  return {
    state: {
      S_s:  Math.max(0.1, S_s + dS_s),
      S_NH: Math.max(0.05, S_NH + dS_NH),
      X_H:  Math.max(100, Math.min(5000, X_H + dX_H * 100)),
      X_A:  Math.max(10, Math.min(500, X_A + dX_A * 20)),
      DO:   Math.max(0.01, Math.min(12, DO + dDO)),
      MLSS: Math.max(500, Math.min(8000, 0.6 * X_H + 0.1 * X_A + 200)),
    },
    sensors: {
      DO:       Math.max(0, DO + dDO + noise(0.05)),
      pH:       Math.max(5, Math.min(10, 7.2 - 0.015 * (S_NH - 20) + noise(0.02))),
      NTU:      Math.max(0.1, turbidity_raw + noise(0.3)),
      NH4:      Math.max(0, S_NH + dS_NH + noise(0.5)),
      COD_est:  Math.max(5, S_s * 1.1 + X_H * 0.08 + noise(3)),
      MLSS_est: Math.max(200, 0.6 * X_H + noise(50)),
      T:        T + noise(0.1),
    }
  };
}

// ─── Colour scheme ─────────────────────────────────────────────────────────
const C = {
  bg:       "#0a0e1a",
  surface:  "#111827",
  card:     "#1a2235",
  border:   "#1e3a5f",
  accent:   "#00d4ff",
  green:    "#00ff9d",
  yellow:   "#ffd700",
  orange:   "#ff8c00",
  red:      "#ff3366",
  teal:     "#00b4d8",
  purple:   "#a78bfa",
  text:     "#e2e8f0",
  muted:    "#64748b",
};

const SCENARIOS = {
  steady:    { label: "稳态标准", S_s_in: 150, S_NH_in: 30, Q_in: 25, T: 22 },
  shock:     { label: "高负荷冲击", S_s_in: 380, S_NH_in: 75, Q_in: 40, T: 24 },
  winter:    { label: "冬季低温", S_s_in: 120, S_NH_in: 28, Q_in: 20, T: 8 },
  summer:    { label: "夏季高温", S_s_in: 220, S_NH_in: 45, Q_in: 35, T: 32 },
  fault_do:  { label: "DO传感器故障", S_s_in: 150, S_NH_in: 30, Q_in: 25, T: 22, fault: "DO_stuck" },
};

// ─── Gauge component ───────────────────────────────────────────────────────
function Gauge({ label, value, unit, min, max, target, color, decimals = 2, alarm }) {
  const pct = Math.min(1, Math.max(0, (value - min) / (max - min)));
  const tpct = target != null ? (target - min) / (max - min) : null;
  const isAlarm = alarm && (value < alarm.low || value > alarm.high);
  const displayColor = isAlarm ? C.red : color;

  return (
    <div style={{
      background: C.card, border: `1px solid ${isAlarm ? C.red : C.border}`,
      borderRadius: 12, padding: "14px 16px", minWidth: 130,
      boxShadow: isAlarm ? `0 0 16px ${C.red}44` : "none",
      transition: "all 0.3s",
    }}>
      <div style={{ color: C.muted, fontSize: 11, letterSpacing: 1, marginBottom: 6, textTransform: "uppercase" }}>{label}</div>
      <div style={{ color: displayColor, fontSize: 26, fontWeight: 700, fontFamily: "monospace", lineHeight: 1 }}>
        {isAlarm && alarm?.sensorFault ? "—.—" : value?.toFixed(decimals)}
        <span style={{ fontSize: 12, marginLeft: 4, color: C.muted }}>{unit}</span>
      </div>
      {/* Progress bar */}
      <div style={{ marginTop: 8, height: 4, background: "#1e293b", borderRadius: 2, position: "relative" }}>
        <div style={{ height: "100%", width: `${pct * 100}%`, background: displayColor, borderRadius: 2, transition: "width 0.3s" }} />
        {tpct != null && (
          <div style={{ position: "absolute", top: -3, left: `${tpct * 100}%`, width: 2, height: 10, background: "#fff8", borderRadius: 1 }} />
        )}
      </div>
      {isAlarm && <div style={{ marginTop: 5, fontSize: 10, color: C.red }}>⚠ ALARM</div>}
    </div>
  );
}

// ─── Slider control ────────────────────────────────────────────────────────
function ControlSlider({ label, value, min, max, step, unit, onChange, color = C.accent, disabled }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ color: C.muted, fontSize: 12 }}>{label}</span>
        <span style={{ color, fontSize: 13, fontFamily: "monospace", fontWeight: 600 }}>
          {value?.toFixed(1)} {unit}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step}
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        disabled={disabled}
        style={{
          width: "100%", accentColor: color,
          opacity: disabled ? 0.4 : 1,
        }}
      />
    </div>
  );
}

// ─── Main App ──────────────────────────────────────────────────────────────
export default function HILSimulator() {
  const [running, setRunning] = useState(false);
  const [autoControl, setAutoControl] = useState(true);
  const [scenario, setScenario] = useState("steady");
  const [simTime, setSimTime] = useState(0);  // seconds

  // Control setpoints
  const [ctrl, setCtrl] = useState({ Q_air: 6.0, D_PAC: 3.0, D_NaOH: 0.5 });
  const [DO_sp, setDO_sp] = useState(2.5);

  // Disturbance
  const [dist, setDist] = useState({ S_s_in: 150, S_NH_in: 30, Q_in: 25, T: 22 });
  const [fault, setFault] = useState(null);

  // Model state
  const stateRef = useRef({
    S_s: 100, S_NH: 25, X_H: 1500, X_A: 180, DO: 2.0, MLSS: 2800
  });
  const [sensors, setSensors] = useState({
    DO: 2.0, pH: 7.2, NTU: 5.0, NH4: 20.0, COD_est: 85, MLSS_est: 2800, T: 22
  });
  const [history, setHistory] = useState([]);
  const [energy, setEnergy] = useState(0);
  const [doseSaved, setDoseSaved] = useState(0);
  const timerRef = useRef(null);

  // PID controller (DO)
  const pidRef = useRef({ integral: 0, prev_err: 0 });

  const autoPID = useCallback((DO_meas, NH4_in) => {
    const DO_sp_auto = Math.min(4.5, Math.max(1.0, 1.5 + 0.6 * (NH4_in / 20)));
    setDO_sp(DO_sp_auto);
    const err = DO_sp_auto - DO_meas;
    pidRef.current.integral = Math.max(-5, Math.min(5, pidRef.current.integral + err * 0.1));
    const d_err = err - pidRef.current.prev_err;
    pidRef.current.prev_err = err;
    const Q_air = Math.max(0.5, Math.min(18, 1.2 * err + 0.08 * pidRef.current.integral + 0.2 * d_err + 5.5));
    return Q_air;
  }, []);

  const autoDosing = useCallback((NTU_in, pH_meas, NH4_in) => {
    const D_PAC = Math.max(0.5, Math.min(12, 0.04 * NTU_in + 0.8));
    const D_NaOH = Math.max(0, Math.min(4, (7.2 - pH_meas) * 1.5));
    return { D_PAC, D_NaOH };
  }, []);

  const step = useCallback(() => {
    const sc = SCENARIOS[scenario];
    const disturbance = { ...dist };

    // Auto control
    let inputs = { ...disturbance };
    if (autoControl) {
      const Q_air = autoPID(stateRef.current.DO, disturbance.S_NH_in);
      const { D_PAC, D_NaOH } = autoDosing(disturbance.S_s_in * 0.05, stateRef.current.S_NH < 30 ? 7.1 : 7.3, disturbance.S_NH_in);
      setCtrl({ Q_air, D_PAC, D_NaOH });
      inputs = { ...disturbance, Q_air, D_PAC, D_NaOH };
    } else {
      inputs = { ...disturbance, ...ctrl };
    }

    // Model step (0.5s virtual time per real 100ms)
    const result = asm1Step(stateRef.current, inputs, 0.5);
    stateRef.current = result.state;

    // Apply fault injection
    const sensorOut = { ...result.sensors };
    if (fault === "DO_stuck") sensorOut.DO = 2.0 + (Math.random() - 0.5) * 0.02;

    setSensors(sensorOut);
    setSimTime(t => t + 0.5);

    // Energy calc (kWh equivalent)
    setEnergy(e => e + inputs.Q_air * 0.5 / 3600 * 0.004);

    // Dose savings vs constant dosing
    const baseline_PAC = 4.0;
    const saved = Math.max(0, baseline_PAC - inputs.D_PAC) * 0.5 / 3600;
    setDoseSaved(d => d + saved);

    setHistory(h => {
      const pt = {
        t: Math.round(simTime + 0.5),
        DO: +sensorOut.DO.toFixed(2),
        NH4: +sensorOut.NH4.toFixed(1),
        NTU: +sensorOut.NTU.toFixed(1),
        COD: +sensorOut.COD_est.toFixed(0),
        Q_air: +inputs.Q_air.toFixed(1),
        D_PAC: +inputs.D_PAC.toFixed(2),
        DO_sp: +DO_sp.toFixed(2),
      };
      return [...h.slice(-300), pt];
    });
  }, [autoControl, ctrl, dist, scenario, fault, autoPID, autoDosing, DO_sp, simTime]);

  useEffect(() => {
    if (running) {
      timerRef.current = setInterval(step, 100);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [running, step]);

  // Apply scenario
  const applyScenario = (key) => {
    setScenario(key);
    const sc = SCENARIOS[key];
    setDist({ S_s_in: sc.S_s_in, S_NH_in: sc.S_NH_in, Q_in: sc.Q_in, T: sc.T });
    setFault(sc.fault || null);
  };

  const formatTime = (s) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
  };

  const doAlarm = { low: 0.3, high: 8.0 };
  const nhAlarm = { low: 0, high: 8.0 };
  const ntuAlarm = { low: 0, high: 5.0 };
  const DOsensorFault = fault === "DO_stuck";

  return (
    <div style={{
      background: C.bg, minHeight: "100vh", color: C.text,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
      padding: "20px",
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 11, color: C.accent, letterSpacing: 3, textTransform: "uppercase" }}>
            AquaMind · HIL
          </div>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#fff" }}>
            精准加药-精准曝气 硬件在环仿真平台
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
          {/* Sim time */}
          <div style={{
            background: C.card, border: `1px solid ${C.border}`, borderRadius: 8,
            padding: "6px 14px", fontSize: 13,
          }}>
            ⏱ 仿真时间：<span style={{ color: C.accent }}>{formatTime(simTime)}</span>
          </div>
          {/* Run/Stop */}
          <button
            onClick={() => setRunning(r => !r)}
            style={{
              background: running ? C.red + "22" : C.green + "22",
              border: `1px solid ${running ? C.red : C.green}`,
              color: running ? C.red : C.green,
              borderRadius: 8, padding: "8px 20px", cursor: "pointer",
              fontFamily: "inherit", fontSize: 13, fontWeight: 700,
              transition: "all 0.2s",
            }}
          >
            {running ? "⏹ STOP" : "▶ START"}
          </button>
          <button
            onClick={() => {
              setRunning(false);
              setHistory([]);
              setSimTime(0);
              setEnergy(0);
              setDoseSaved(0);
              pidRef.current = { integral: 0, prev_err: 0 };
              stateRef.current = { S_s: 100, S_NH: 25, X_H: 1500, X_A: 180, DO: 2.0, MLSS: 2800 };
            }}
            style={{
              background: "transparent", border: `1px solid ${C.border}`,
              color: C.muted, borderRadius: 8, padding: "8px 14px",
              cursor: "pointer", fontFamily: "inherit", fontSize: 12,
            }}
          >↺ RESET</button>
        </div>
      </div>

      {/* Fault banner */}
      {fault && (
        <div style={{
          background: C.red + "22", border: `1px solid ${C.red}`,
          borderRadius: 8, padding: "10px 16px", marginBottom: 16,
          color: C.red, fontSize: 13,
          animation: "pulse 1s infinite",
        }}>
          ⚠ 故障注入激活：{fault === "DO_stuck" ? "DO 传感器卡死（固定读数 2.0 mg/L）" : fault}
          ——测试 SafetyWatcher 检测响应
          <button onClick={() => setFault(null)} style={{
            marginLeft: 12, background: "none", border: "none", color: C.red,
            cursor: "pointer", fontSize: 12, textDecoration: "underline",
          }}>清除故障</button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 20 }}>
        {/* Sensor gauges */}
        <div style={{ gridColumn: "1/3" }}>
          <div style={{ fontSize: 11, color: C.muted, letterSpacing: 2, marginBottom: 10, textTransform: "uppercase" }}>
            ▸ 虚拟传感器读数（含延迟+噪声+漂移仿真）
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Gauge label="溶解氧 DO" value={DOsensorFault ? 2.0 : sensors.DO}
              unit="mg/L" min={0} max={10} target={DO_sp} color={C.accent}
              alarm={{ ...doAlarm, sensorFault: DOsensorFault }} decimals={2} />
            <Gauge label="pH 值" value={sensors.pH}
              unit="" min={5} max={10} target={7.2} color={C.green} decimals={2}
              alarm={{ low: 5.5, high: 9.0 }} />
            <Gauge label="浊度 NTU" value={sensors.NTU}
              unit="NTU" min={0} max={30} target={1.0} color={C.yellow}
              alarm={{ low: 0, high: 5 }} decimals={1} />
            <Gauge label="氨氮 NH4⁺" value={sensors.NH4}
              unit="mg/L" min={0} max={50} target={5.0} color={C.orange}
              alarm={nhAlarm} decimals={1} />
            <Gauge label="COD（预测）" value={sensors.COD_est}
              unit="mg/L" min={0} max={200} target={30} color={C.teal} decimals={0} />
            <Gauge label="MLSS" value={sensors.MLSS_est}
              unit="mg/L" min={0} max={6000} color={C.purple} decimals={0} />
          </div>
        </div>

        {/* Performance KPIs */}
        <div>
          <div style={{ fontSize: 11, color: C.muted, letterSpacing: 2, marginBottom: 10, textTransform: "uppercase" }}>
            ▸ 实时性能指标
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { label: "能耗累计", val: energy.toFixed(4), unit: "kWh", c: C.yellow },
              { label: "加药节省", val: (doseSaved * 1000).toFixed(1), unit: "mL PAC", c: C.green },
              { label: "DO 设定点", val: DO_sp.toFixed(2), unit: "mg/L", c: C.accent },
              { label: "进水浊度", val: (dist.S_s_in * 0.05).toFixed(1), unit: "NTU", c: C.teal },
              { label: "进水温度", val: dist.T.toFixed(1), unit: "°C", c: C.orange },
            ].map(({ label, val, unit, c }) => (
              <div key={label} style={{
                background: C.card, border: `1px solid ${C.border}`,
                borderRadius: 8, padding: "8px 12px",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                <span style={{ color: C.muted, fontSize: 11 }}>{label}</span>
                <span style={{ color: c, fontSize: 14, fontWeight: 600 }}>{val} <span style={{ color: C.muted, fontSize: 10 }}>{unit}</span></span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 16, marginBottom: 16 }}>
        {/* Control panel */}
        <div style={{
          background: C.card, border: `1px solid ${C.border}`,
          borderRadius: 12, padding: 16,
        }}>
          <div style={{ fontSize: 11, color: C.muted, letterSpacing: 2, marginBottom: 14, textTransform: "uppercase" }}>
            ▸ 控制参数
          </div>

          {/* Auto/Manual toggle */}
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {["自动PID", "手动"].map((label, i) => (
              <button key={label} onClick={() => setAutoControl(i === 0)} style={{
                flex: 1, padding: "6px 0",
                background: autoControl === (i === 0) ? C.accent + "22" : "transparent",
                border: `1px solid ${autoControl === (i === 0) ? C.accent : C.border}`,
                color: autoControl === (i === 0) ? C.accent : C.muted,
                borderRadius: 6, cursor: "pointer", fontSize: 12, fontFamily: "inherit",
              }}>{label}</button>
            ))}
          </div>

          <ControlSlider label="曝气量 Q_air" value={ctrl.Q_air}
            min={0.5} max={18} step={0.1} unit="L/min"
            color={C.accent} disabled={autoControl}
            onChange={v => setCtrl(c => ({ ...c, Q_air: v }))} />
          <ControlSlider label="PAC 投量" value={ctrl.D_PAC}
            min={0.1} max={12} step={0.1} unit="mL/min"
            color={C.yellow} disabled={autoControl}
            onChange={v => setCtrl(c => ({ ...c, D_PAC: v }))} />
          <ControlSlider label="NaOH 投量" value={ctrl.D_NaOH}
            min={0} max={4} step={0.05} unit="mL/min"
            color={C.green} disabled={autoControl}
            onChange={v => setCtrl(c => ({ ...c, D_NaOH: v }))} />

          <div style={{ borderTop: `1px solid ${C.border}`, marginTop: 12, paddingTop: 12 }}>
            <div style={{ fontSize: 11, color: C.muted, marginBottom: 10, letterSpacing: 1 }}>▸ 进水扰动（场景）</div>
            {Object.entries(SCENARIOS).map(([key, sc]) => (
              <button key={key} onClick={() => applyScenario(key)} style={{
                display: "block", width: "100%", textAlign: "left",
                padding: "5px 10px", marginBottom: 4,
                background: scenario === key ? C.accent + "1a" : "transparent",
                border: `1px solid ${scenario === key ? C.accent : C.border}`,
                color: scenario === key ? C.accent : C.muted,
                borderRadius: 6, cursor: "pointer", fontSize: 11, fontFamily: "inherit",
              }}>{sc.label}</button>
            ))}
          </div>
        </div>

        {/* Charts */}
        <div style={{ display: "grid", gridTemplateRows: "1fr 1fr", gap: 12 }}>
          {/* DO chart */}
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 12, padding: "12px 16px" }}>
            <div style={{ fontSize: 11, color: C.muted, letterSpacing: 2, marginBottom: 8 }}>
              DO 控制（级联PID · 内环）
            </div>
            <ResponsiveContainer width="100%" height={140}>
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                <XAxis dataKey="t" tick={{ fill: C.muted, fontSize: 9 }}
                  tickFormatter={v => formatTime(v)} />
                <YAxis domain={[0, 6]} tick={{ fill: C.muted, fontSize: 9 }} />
                <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, fontSize: 11 }}
                  formatter={(v, n) => [v, n === "DO" ? "DO (mg/L)" : "设定点"]} />
                <Line dataKey="DO" stroke={C.accent} dot={false} strokeWidth={2} isAnimationActive={false} />
                <Line dataKey="DO_sp" stroke={C.accent} dot={false} strokeWidth={1}
                  strokeDasharray="4 2" isAnimationActive={false} />
                <Line dataKey="Q_air" stroke={C.purple} dot={false} strokeWidth={1.5}
                  yAxisId="right" isAnimationActive={false} />
                <YAxis yAxisId="right" orientation="right" domain={[0, 20]}
                  tick={{ fill: C.muted, fontSize: 9 }} />
                <ReferenceLine y={0.5} stroke={C.red} strokeDasharray="2 2" strokeWidth={1} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Water quality chart */}
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 12, padding: "12px 16px" }}>
            <div style={{ fontSize: 11, color: C.muted, letterSpacing: 2, marginBottom: 8 }}>
              出水水质（NH4⁺ · NTU · COD/10）
            </div>
            <ResponsiveContainer width="100%" height={140}>
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                <XAxis dataKey="t" tick={{ fill: C.muted, fontSize: 9 }}
                  tickFormatter={v => formatTime(v)} />
                <YAxis domain={[0, 50]} tick={{ fill: C.muted, fontSize: 9 }} />
                <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, fontSize: 11 }} />
                <Line dataKey="NH4" stroke={C.orange} dot={false} strokeWidth={2} isAnimationActive={false} />
                <Line dataKey="NTU" stroke={C.yellow} dot={false} strokeWidth={1.5} isAnimationActive={false} />
                <Line dataKey={pt => pt.COD / 10} stroke={C.teal} dot={false} strokeWidth={1.5}
                  name="COD/10" isAnimationActive={false} />
                <ReferenceLine y={5} stroke={C.orange} strokeDasharray="3 2" strokeWidth={1} label={{ value: "NH4限值", fill: C.orange, fontSize: 9 }} />
                <ReferenceLine y={1} stroke={C.yellow} strokeDasharray="3 2" strokeWidth={1} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom status bar */}
      <div style={{
        background: C.card, border: `1px solid ${C.border}`, borderRadius: 8,
        padding: "8px 16px", display: "flex", gap: 24, alignItems: "center",
        fontSize: 11, color: C.muted,
      }}>
        <span>◉ <span style={{ color: running ? C.green : C.red }}>{running ? "RUNNING" : "STOPPED"}</span></span>
        <span>模型步长: <span style={{ color: C.accent }}>500ms</span></span>
        <span>控制模式: <span style={{ color: autoControl ? C.green : C.yellow }}>{autoControl ? "自动PID" : "手动"}</span></span>
        <span>场景: <span style={{ color: C.teal }}>{SCENARIOS[scenario].label}</span></span>
        <span>故障: <span style={{ color: fault ? C.red : C.green }}>{fault || "无"}</span></span>
        <span style={{ marginLeft: "auto" }}>CHS · AquaMind-HIL v1.0 · HydroClaw</span>
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.7} }
        input[type=range] { height: 4px; }
      `}</style>
    </div>
  );
}
