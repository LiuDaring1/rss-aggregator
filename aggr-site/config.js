/**
 * aggr-site 统一运行模式与配置解析
 * 集中管理只读模式（AGGR_READONLY, AGGR_MODE=readonly）与离线模式（AGGR_OFFLINE, AGGR_MODE=offline）
 */

export function isReadOnlyMode() {
  const ro = (process.env.AGGR_READONLY || '').trim().toLowerCase();
  const mode = (process.env.AGGR_MODE || '').trim().toLowerCase();
  return ro === 'on' || ro === '1' || ro === 'true' || mode === 'readonly' || mode.includes('readonly');
}

export function isOfflineMode() {
  const off = (process.env.AGGR_OFFLINE || '').trim().toLowerCase();
  const mode = (process.env.AGGR_MODE || '').trim().toLowerCase();
  return off === 'on' || off === '1' || off === 'true' || mode === 'offline' || mode.includes('offline');
}
