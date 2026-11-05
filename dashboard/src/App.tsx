import { useEffect, useMemo, useState } from 'react'
import {
  Activity, ArrowDownRight, ArrowUpRight, BarChart3, ChevronDown,
  CircleDollarSign, Clock3, Coins, Database, Gauge, Layers3,
  Menu, RefreshCw, ShieldCheck, Sparkles, X,
  type LucideIcon,
} from 'lucide-react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

type Point = { date: string; period_end?: string; source_date?: string; value: number; observations?: number }
type Metric = {
  label: string; kind: 'flow' | 'stock'; unit: string; aggregation: string;
  observation_count: number; first_date: string | null; last_date: string | null;
  daily: Point[]; weekly: Point[]; monthly: Point[]
}
type AllTimeMetric = { value: number; unit: string; source: string; updated_at: string; methodology?: string }
type DashboardData = {
  schema_version: number; generated_at: string; source_scope: string;
  all_time: Record<string, AllTimeMetric>; series: Record<string, Metric>
}

type TabId = 'overview' | 'market' | 'fees' | 'daily-revenue' | 'intents'
type Interval = 'daily' | 'weekly' | 'monthly'
type Range = '30D' | '90D' | '1Y' | 'ALL'
type ChartLine = { key: string; label: string; color: string }
type TooltipItem = { value?: number | string; color?: string; name?: string; payload?: Point }

const tabs: { id: TabId; label: string; icon: LucideIcon; eyebrow: string }[] = [
  { id: 'overview', label: 'Overview', icon: Gauge, eyebrow: 'ECOSYSTEM PULSE' },
  { id: 'market', label: 'Market Activity', icon: BarChart3, eyebrow: 'ON-CHAIN MARKETS' },
  { id: 'fees', label: 'Fee & Revenue Performance', icon: CircleDollarSign, eyebrow: 'VALUE GENERATED' },
  { id: 'daily-revenue', label: 'NEAR Daily Revenue & Fees', icon: Activity, eyebrow: 'DAILY ECONOMICS' },
  { id: 'intents', label: 'NEAR Intents', icon: Layers3, eyebrow: 'INTENTS ECOSYSTEM' },
]

const intervalOptions: { id: Interval; label: string }[] = [
  { id: 'daily', label: 'Daily' }, { id: 'weekly', label: 'Weekly' }, { id: 'monthly', label: 'Monthly' },
]
const rangeOptions: Range[] = ['30D', '90D', '1Y', 'ALL']

const moneyFull = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })
const moneyCompact = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2 })

function money(value: number | undefined | null, full = false) {
  if (value === undefined || value === null || !Number.isFinite(value)) return '—'
  return (full ? moneyFull : moneyCompact).format(value)
}

function shortDate(value?: string) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
}

function chartDate(value: string, interval: Interval) {
  const day = new Date(`${value}T00:00:00Z`)
  if (interval === 'monthly') return new Intl.DateTimeFormat('en-US', { month: 'short', year: '2-digit', timeZone: 'UTC' }).format(day)
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' }).format(day)
}

function percentChange(current?: number, previous?: number) {
  if (current === undefined || previous === undefined || previous === 0) return undefined
  return ((current - previous) / Math.abs(previous)) * 100
}

function getPoints(data: DashboardData | null, id: string, interval: Interval, range: Range): Point[] {
  const metric = data?.series[id]
  if (!metric) return []
  const rows = metric[interval]
  if (range === 'ALL' || !rows.length) return rows
  const lastDate = rows[rows.length - 1].date
  const anchor = new Date(`${lastDate}T00:00:00Z`)
  const days = range === '30D' ? 30 : range === '90D' ? 90 : 365
  anchor.setUTCDate(anchor.getUTCDate() - days + 1)
  const cutoff = anchor.toISOString().slice(0, 10)
  return rows.filter((row) => row.date >= cutoff)
}

function latestValue(data: DashboardData | null, id: string, interval: Interval, range: Range) {
  const rows = getPoints(data, id, interval, range)
  return rows.at(-1)?.value
}

function deltaValue(data: DashboardData | null, id: string, interval: Interval, range: Range) {
  const rows = getPoints(data, id, interval, range)
  return percentChange(rows.at(-1)?.value, rows.at(-2)?.value)
}

function KpiCard({
  label, value, caption, icon: Icon, accent, delta,
}: { label: string; value: string; caption: string; icon: LucideIcon; accent: string; delta?: number }) {
  return (
    <article className="kpi-card surface-card">
      <div className="kpi-topline">
        <span className={`kpi-icon ${accent}`}><Icon size={18} strokeWidth={1.9} /></span>
        {delta !== undefined && Number.isFinite(delta) && (
          <span className={`delta-pill ${delta >= 0 ? 'positive' : 'negative'}`}>
            {delta >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>
      <p className="kpi-label">{label}</p>
      <p className="kpi-value">{value}</p>
      <p className="kpi-caption">{caption}</p>
    </article>
  )
}

function ChartTooltip({ active, payload, label, interval }: {
  active?: boolean; payload?: ReadonlyArray<TooltipItem>; label?: string; interval: Interval
}) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  const dateLabel = row?.date ? chartDate(row.date, interval) : label
  return (
    <div className="chart-tooltip">
      <p className="tooltip-date">{dateLabel}{row?.period_end && row.period_end !== row.date ? ` – ${chartDate(row.period_end, interval)}` : ''}</p>
      {payload.map((item, index) => (
        <div className="tooltip-line" key={`${item.name}-${index}`}>
          <span className="tooltip-dot" style={{ background: item.color }} />
          <span>{item.name}</span>
          <strong>{money(Number(item.value), true)}</strong>
        </div>
      ))}
    </div>
  )
}

function ChartPanel({
  title, subtitle, data, lines, interval, variant = 'area', height = 288, footer,
}: {
  title: string; subtitle: string; data: Point[]; lines: ChartLine[]; interval: Interval;
  variant?: 'area' | 'line' | 'bar'; height?: number; footer?: string
}) {
  const Chart = variant === 'bar' ? BarChart : variant === 'line' ? LineChart : AreaChart
  return (
    <section className="chart-panel surface-card">
      <div className="panel-heading">
        <div><h3>{title}</h3><p>{subtitle}</p></div>
        <button className="icon-button subtle-button" aria-label={`More about ${title}`} title="Daily source observations, aggregated by selected interval">
          <ChevronDown size={16} />
        </button>
      </div>
      {data.length ? (
        <div className="chart-wrap" style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            <Chart data={data} margin={{ top: 10, right: 6, left: -18, bottom: 2 }}>
              <CartesianGrid stroke="#EDF1F6" vertical={false} />
              <XAxis dataKey="date" tickFormatter={(value) => chartDate(String(value), interval)} tickLine={false} axisLine={false} minTickGap={32} tick={{ fill: '#8993A5', fontSize: 11 }} dy={10} />
              <YAxis tickFormatter={(value) => money(Number(value))} tickLine={false} axisLine={false} width={64} tick={{ fill: '#8993A5', fontSize: 11 }} />
              <Tooltip content={({ active, payload, label }) => <ChartTooltip active={active} payload={payload as unknown as ReadonlyArray<TooltipItem>} label={String(label ?? '')} interval={interval} />} cursor={{ fill: '#F4F7FA' }} />
              {variant === 'area' && lines.map((line) => (
                <Area key={line.key} type="monotone" dataKey={line.key} name={line.label} stroke={line.color} strokeWidth={2.5} fill={`url(#fill-${line.key})`} activeDot={{ r: 4, strokeWidth: 0 }} connectNulls={false} />
              ))}
              {variant === 'line' && lines.map((line) => (
                <Line key={line.key} type="monotone" dataKey={line.key} name={line.label} stroke={line.color} strokeWidth={2.3} dot={false} activeDot={{ r: 4, strokeWidth: 0 }} connectNulls={false} />
              ))}
              {variant === 'bar' && lines.map((line) => (
                <Bar key={line.key} dataKey={line.key} name={line.label} fill={line.color} radius={[4, 4, 0, 0]} maxBarSize={24} />
              ))}
              {variant === 'area' && <defs>{lines.map((line) => (
                <linearGradient key={line.key} id={`fill-${line.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={line.color} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={line.color} stopOpacity={0.015} />
                </linearGradient>
              ))}</defs>}
            </Chart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="empty-chart"><Database size={20} /><span>No observations for this range yet.</span></div>
      )}
      <div className="chart-footer">
        {lines.length > 1 && <div className="legend-row">{lines.map((line) => <span className="legend-item" key={line.key}><i style={{ background: line.color }} />{line.label}</span>)}</div>}
        {footer && <span className="chart-note">{footer}</span>}
      </div>
    </section>
  )
}

function SummaryPanel({ title, subtitle, metrics, data }: { title: string; subtitle: string; metrics: string[]; data: DashboardData }) {
  return (
    <section className="summary-panel surface-card">
      <div className="panel-heading"><div><h3>{title}</h3><p>{subtitle}</p></div><span className="tiny-status"><span />LIFETIME</span></div>
      <div className="summary-list">
        {metrics.map((id) => {
          const metric = data.all_time[id]
          if (!metric) return null
          return <div className="summary-row" key={id}><div><span className="summary-name">{prettyMetricName(id)}</span><small>{metric.source} · cumulative</small></div><strong>{money(metric.value)}</strong></div>
        })}
      </div>
    </section>
  )
}

function prettyMetricName(id: string) {
  const names: Record<string, string> = {
    near_network_dex_volume: 'NEAR DEX volume', near_network_fees: 'NEAR network fees',
    near_intents_dex_volume: 'NEAR Intents DEX volume', near_intents_gross_fees: 'NEAR Intents gross fees',
    near_intents_net_revenue: 'NEAR Intents net revenue', near_intents_holders_revenue_buyback: 'NEAR Intents holders revenue',
    current_chain_tvl: 'Current chain TVL', current_stablecoin_supply: 'Current stablecoin supply',
  }
  return names[id] ?? id.replaceAll('_', ' ')
}

function DataUnavailable() {
  return <div className="loading-screen"><div className="loading-mark">N</div><p>Loading NEAR analytics…</p></div>
}

function App() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<TabId>('overview')
  const [interval, setInterval] = useState<Interval>('daily')
  const [range, setRange] = useState<Range>('90D')
  const [mobileOpen, setMobileOpen] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const url = `${import.meta.env.BASE_URL}data/dashboard.json?t=${Date.now()}`
      const response = await fetch(url, { cache: 'no-store' })
      if (!response.ok) throw new Error(`Dashboard data returned ${response.status}`)
      setData(await response.json() as DashboardData)
      setError('')
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load dashboard data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadData() }, [])

  const activeTab = tabs.find((item) => item.id === tab) ?? tabs[0]
  const anchorDate = useMemo(() => {
    if (!data) return undefined
    return Object.values(data.series).map((metric) => metric.last_date).filter(Boolean).sort().at(-1) ?? undefined
  }, [data])
  const updatedAt = data?.generated_at ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }).format(new Date(data.generated_at)) + ' UTC' : ''

  const currentTvl = data?.all_time.current_chain_tvl?.value ?? latestValue(data, 'network_tvl', interval, range)
  const currentStablecoins = data?.all_time.current_stablecoin_supply?.value ?? latestValue(data, 'stablecoin_supply', interval, range)
  const windowVolume = latestValue(data, 'network_dex_volume', interval, range)
  const windowFees = latestValue(data, 'network_fees', interval, range)
  const currentRangeLabel = interval === 'daily' ? 'Latest daily observation' : interval === 'weekly' ? 'Latest weekly total' : 'Latest monthly total'

  if (loading && !data) return <DataUnavailable />

  const chartRows = (id: string) => getPoints(data, id, interval, range)
  const metricRows = (ids: string[]) => {
    const maps = ids.map((id) => new Map(chartRows(id).map((point) => [point.date, point.value])))
    const dates = [...new Set(maps.flatMap((map) => [...map.keys()]))].sort()
    return dates.map((date) => Object.fromEntries([['date', date], ...maps.map((map, index) => [ids[index], map.get(date) ?? null])])) as Point[]
  }

  const renderOverview = () => (
    <>
      <div className="kpi-grid">
        <KpiCard label="NEAR chain TVL" value={money(currentTvl)} caption="Current DeFi value locked" icon={Layers3} accent="mint" />
        <KpiCard label="Stablecoin supply" value={money(currentStablecoins)} caption="Current circulating value" icon={Coins} accent="blue" />
        <KpiCard label="NEAR DEX volume" value={money(windowVolume)} caption={currentRangeLabel} icon={BarChart3} accent="violet" delta={deltaValue(data, 'network_dex_volume', interval, range)} />
        <KpiCard label="Network fees" value={money(windowFees)} caption={currentRangeLabel} icon={CircleDollarSign} accent="amber" delta={deltaValue(data, 'network_fees', interval, range)} />
      </div>
      <div className="chart-grid two-columns">
        <ChartPanel title="NEAR DEX trading volume" subtitle={`${range === 'ALL' ? 'All available history' : `Last ${range}`} · ${interval} aggregation`} data={chartRows('network_dex_volume')} lines={[{ key: 'value', label: 'Trading volume', color: '#16B98A' }]} interval={interval} variant="area" footer={`Flow metric · ${interval === 'daily' ? 'daily value' : 'period total'}`} />
        <ChartPanel title="NEAR network TVL" subtitle="Total value locked on the NEAR chain" data={chartRows('network_tvl')} lines={[{ key: 'value', label: 'TVL', color: '#6477E8' }]} interval={interval} variant="line" footer="Stock metric · last observation in each period" />
      </div>
      <div className="chart-grid two-columns lower-grid">
        <ChartPanel title="Network fees" subtitle="Fees paid by users across tracked NEAR protocols" data={chartRows('network_fees')} lines={[{ key: 'value', label: 'Network fees', color: '#F59E0B' }]} interval={interval} variant="bar" />
        <ChartPanel title="Stablecoin supply" subtitle="Aggregate circulating stablecoin value" data={chartRows('stablecoin_supply')} lines={[{ key: 'value', label: 'Stablecoin supply', color: '#22A5D9' }]} interval={interval} variant="area" footer="Stock metric · last observation in each period" />
      </div>
      {data && <SummaryPanel title="Lifetime network activity" subtitle="Cumulative flow totals reported by DeFiLlama" metrics={['near_network_dex_volume', 'near_network_fees']} data={data} />}
    </>
  )

  const renderMarket = () => (
    <>
      <div className="kpi-grid compact-kpis">
        <KpiCard label="Latest DEX volume" value={money(windowVolume)} caption={currentRangeLabel} icon={BarChart3} accent="mint" />
        <KpiCard label="Latest stablecoin supply" value={money(currentStablecoins)} caption="Current snapshot" icon={Coins} accent="blue" />
        <KpiCard label="NEAR Intents volume" value={money(latestValue(data, 'intents_dex_volume', interval, range))} caption={currentRangeLabel} icon={Activity} accent="violet" />
      </div>
      <div className="chart-grid two-columns">
        <ChartPanel title="NEAR DEX volume" subtitle="All tracked DEX protocols on the chain" data={chartRows('network_dex_volume')} lines={[{ key: 'value', label: 'NEAR network', color: '#16B98A' }]} interval={interval} variant="area" />
        <ChartPanel title="NEAR Intents DEX volume" subtitle="Protocol-level trading activity" data={chartRows('intents_dex_volume')} lines={[{ key: 'value', label: 'NEAR Intents', color: '#8B75E8' }]} interval={interval} variant="area" />
      </div>
      <div className="chart-grid two-columns lower-grid">
        <ChartPanel title="Stablecoin supply" subtitle="USD value by observation date" data={chartRows('stablecoin_supply')} lines={[{ key: 'value', label: 'Stablecoins', color: '#22A5D9' }]} interval={interval} variant="line" footer="Stock metric · period-end observation" />
        <ChartPanel title="NEAR network TVL" subtitle="DeFi TVL excluding double-counted value" data={chartRows('network_tvl')} lines={[{ key: 'value', label: 'TVL', color: '#6477E8' }]} interval={interval} variant="line" footer="Stock metric · period-end observation" />
      </div>
    </>
  )

  const renderFees = () => (
    <>
      {data && <SummaryPanel title="Lifetime fees & revenue" subtitle="Values are cumulative and kept distinct by methodology" metrics={['near_network_fees', 'near_intents_gross_fees', 'near_intents_net_revenue', 'near_intents_holders_revenue_buyback']} data={data} />}
      <div className="chart-grid two-columns lower-grid">
        <ChartPanel title="Network fees vs. Intents gross fees" subtitle="Chain-wide fees and protocol-level fees are separate measures" data={metricRows(['network_fees', 'intents_gross_fees'])} lines={[{ key: 'network_fees', label: 'Network fees', color: '#F0A52B' }, { key: 'intents_gross_fees', label: 'Intents gross fees', color: '#16B98A' }]} interval={interval} variant="line" />
        <ChartPanel title="NEAR Intents captured revenue" subtitle="Net revenue and holders revenue" data={metricRows(['intents_net_revenue', 'intents_holders_revenue'])} lines={[{ key: 'intents_net_revenue', label: 'Net revenue', color: '#6477E8' }, { key: 'intents_holders_revenue', label: 'Holders revenue', color: '#E88066' }]} interval={interval} variant="area" />
      </div>
      <div className="notice-card"><ShieldCheck size={18} /><p><strong>Metric definitions stay separate.</strong> Network fees are user-paid fees across tracked NEAR protocols. NEAR Intents gross fees, net revenue, and holders revenue are distinct protocol metrics; holders revenue does not mean token burn.</p></div>
    </>
  )

  const renderDailyRevenue = () => (
    <>
      <div className="kpi-grid compact-kpis">
        <KpiCard label="Latest network fees" value={money(windowFees)} caption={currentRangeLabel} icon={CircleDollarSign} accent="amber" delta={deltaValue(data, 'network_fees', interval, range)} />
        <KpiCard label="Intents gross fees" value={money(latestValue(data, 'intents_gross_fees', interval, range))} caption={currentRangeLabel} icon={Activity} accent="mint" />
        <KpiCard label="Intents net revenue" value={money(latestValue(data, 'intents_net_revenue', interval, range))} caption={currentRangeLabel} icon={Coins} accent="violet" />
      </div>
      <div className="chart-grid two-columns">
        <ChartPanel title="Daily fees and revenue" subtitle="Use Daily for source values; Weekly and Monthly show period sums" data={metricRows(['network_fees', 'intents_gross_fees', 'intents_net_revenue'])} lines={[{ key: 'network_fees', label: 'Network fees', color: '#F0A52B' }, { key: 'intents_gross_fees', label: 'Intents gross fees', color: '#16B98A' }, { key: 'intents_net_revenue', label: 'Intents net revenue', color: '#6477E8' }]} interval={interval} variant="line" height={340} />
        <ChartPanel title="Holders revenue" subtitle="DeFiLlama daily holders revenue series" data={chartRows('intents_holders_revenue')} lines={[{ key: 'value', label: 'Holders revenue', color: '#E88066' }]} interval={interval} variant="bar" height={340} footer="USD · a revenue classification, not token burn" />
      </div>
      <div className="notice-card"><Clock3 size={18} /><p>Daily observations come from DeFiLlama. Weekly and monthly views sum flow metrics within each bucket; they do not calculate running cumulative totals.</p></div>
    </>
  )

  const renderIntents = () => (
    <>
      <div className="intents-banner">
        <div className="intents-symbol"><Sparkles size={22} /></div>
        <div><span className="banner-kicker">PROTOCOL OVERVIEW</span><h2>NEAR Intents</h2><p>Trading activity, liquidity, and value capture for the protocol.</p></div>
        <div className="banner-updated"><span>Latest data</span><strong>{shortDate(data?.series.intents_dex_volume.last_date ?? undefined)}</strong></div>
      </div>
      <div className="kpi-grid compact-kpis">
        <KpiCard label="Intents TVL" value={money(latestValue(data, 'intents_tvl', interval, range))} caption="Latest period-end value" icon={Layers3} accent="violet" />
        <KpiCard label="DEX trading volume" value={money(latestValue(data, 'intents_dex_volume', interval, range))} caption={currentRangeLabel} icon={BarChart3} accent="mint" />
        <KpiCard label="Gross fees" value={money(latestValue(data, 'intents_gross_fees', interval, range))} caption={currentRangeLabel} icon={CircleDollarSign} accent="amber" />
      </div>
      <div className="chart-grid two-columns">
        <ChartPanel title="NEAR Intents TVL" subtitle="Total protocol TVL; separate chain breakdowns are preserved in source data" data={chartRows('intents_tvl')} lines={[{ key: 'value', label: 'Total TVL', color: '#6477E8' }]} interval={interval} variant="area" footer="Stock metric · period-end observation" />
        <ChartPanel title="NEAR Intents DEX volume" subtitle="Daily trading volume on the protocol" data={chartRows('intents_dex_volume')} lines={[{ key: 'value', label: 'DEX volume', color: '#16B98A' }]} interval={interval} variant="bar" />
      </div>
      <div className="chart-grid two-columns lower-grid">
        <ChartPanel title="Gross fees and net revenue" subtitle="Fees charged vs. revenue captured" data={metricRows(['intents_gross_fees', 'intents_net_revenue'])} lines={[{ key: 'intents_gross_fees', label: 'Gross fees', color: '#F0A52B' }, { key: 'intents_net_revenue', label: 'Net revenue', color: '#6477E8' }]} interval={interval} variant="line" />
        <ChartPanel title="Holders revenue" subtitle="Historical classification per NEAR Intents methodology" data={chartRows('intents_holders_revenue')} lines={[{ key: 'value', label: 'Holders revenue', color: '#E88066' }]} interval={interval} variant="area" />
      </div>
      {data && <SummaryPanel title="Lifetime NEAR Intents totals" subtitle="Cumulative values where reported by DeFiLlama" metrics={['near_intents_dex_volume', 'near_intents_gross_fees', 'near_intents_net_revenue', 'near_intents_holders_revenue_buyback']} data={data} />}
    </>
  )

  const renderTab = () => {
    switch (tab) {
      case 'market': return renderMarket()
      case 'fees': return renderFees()
      case 'daily-revenue': return renderDailyRevenue()
      case 'intents': return renderIntents()
      default: return renderOverview()
    }
  }

  const Sidebar = ({ mobile = false }: { mobile?: boolean }) => (
    <aside className={`sidebar ${mobile ? 'mobile-sidebar' : ''} ${mobileOpen && mobile ? 'open' : ''}`}>
      <div className="brand-lockup">
        <div className="brand-mark"><span /></div>
        <div><strong>NEAR</strong><small>VALUE CAPTURE</small></div>
        {mobile && <button className="mobile-close icon-button" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={19} /></button>}
      </div>
      <div className="side-rule" />
      <p className="nav-heading">ANALYTICS</p>
      <nav className="main-nav" aria-label="Dashboard sections">
        {tabs.map((item, index) => {
          const Icon = item.icon
          return <button className={`nav-item ${tab === item.id ? 'active' : ''}`} key={item.id} onClick={() => { setTab(item.id); setMobileOpen(false) }}>
            <Icon size={18} strokeWidth={1.8} /><span>{item.label}</span>{item.id === 'overview' && <small>{String(index + 1).padStart(2, '0')}</small>}
          </button>
        })}
      </nav>
      <div className="sidebar-spacer" />
      <div className="side-source-card">
        <div className="source-icon"><Database size={16} /></div>
        <div><strong>Data connections</strong><span><i />DeFiLlama active</span></div>
      </div>
      <div className="sidebar-footer"><span>NEAR ecosystem analytics</span><span>v0.1 · Preview</span></div>
    </aside>
  )

  return (
    <div className="app-shell">
      <Sidebar />
      <Sidebar mobile />
      {mobileOpen && <button className="mobile-scrim" aria-label="Close menu" onClick={() => setMobileOpen(false)} />}
      <main className="main-area">
        <header className="topbar">
          <button className="mobile-menu icon-button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={21} /></button>
          <div className="breadcrumb"><span>Dashboard</span><b>/</b><strong>{activeTab.label}</strong></div>
          <div className="topbar-actions">
            <span className="source-pill"><span />DefiLlama data</span>
            <button className={`refresh-button icon-button ${loading ? 'rotating' : ''}`} onClick={() => void loadData()} aria-label="Refresh local dashboard data" title="Reload prepared local data"><RefreshCw size={16} /></button>
            <div className="avatar">N</div>
          </div>
        </header>

        <div className="page-content">
          <section className="page-intro">
            <div>
              <div className="page-eyebrow"><span className="eyebrow-line" />{activeTab.eyebrow}</div>
              <h1>{activeTab.label}</h1>
              <p className="page-subtitle">{tab === 'overview' ? 'A clear view of NEAR network activity and value capture.' : tab === 'intents' ? 'Protocol activity, liquidity, and revenue indicators.' : 'Explore historical activity using daily source data and period-aware aggregation.'}</p>
            </div>
            <div className="data-freshness"><span className="freshness-dot" /><div><span>DATA PREPARED</span><strong>{updatedAt || '—'}</strong></div></div>
          </section>

          <section className="control-row" aria-label="Chart controls">
            <div className="control-group interval-control" role="group" aria-label="Aggregation interval">
              {intervalOptions.map((item) => <button key={item.id} className={interval === item.id ? 'selected' : ''} onClick={() => setInterval(item.id)}>{item.label}</button>)}
            </div>
            <div className="control-right">
              <div className="control-group range-control" role="group" aria-label="Date range">
                {rangeOptions.map((item) => <button key={item} className={range === item ? 'selected' : ''} onClick={() => setRange(item)}>{item}</button>)}
              </div>
              {anchorDate && <span className="range-end">Through {shortDate(anchorDate)}</span>}
            </div>
          </section>

          {error && <div className="error-banner"><Database size={17} /><div><strong>Dashboard data is not ready.</strong><span>{error} Run <code>python ../dashboard-data/build.py</code> from the dashboard directory.</span></div></div>}
          {data && renderTab()}

          <footer className="page-footer"><span>Source: DeFiLlama · Daily observations</span><span>Weekly/monthly flows are summed; stock metrics use the last observation in each period.</span></footer>
        </div>
      </main>
    </div>
  )
}

export default App
