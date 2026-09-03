const CURRENT_USER_STORAGE_KEY = 'tianshui_current_user'

function safeParse(rawValue, fallback = null) {
  if (!rawValue) return fallback
  try {
    return JSON.parse(rawValue)
  } catch {
    return fallback
  }
}

export function setCurrentUserContext(user) {
  if (typeof window === 'undefined') return
  if (!user) {
    localStorage.removeItem(CURRENT_USER_STORAGE_KEY)
    return
  }

  localStorage.setItem(CURRENT_USER_STORAGE_KEY, JSON.stringify({
    id: user.id,
    username: user.username,
    role: user.role,
    role_display: user.role_display,
    is_admin: user.is_admin,
    is_superuser: user.is_superuser,
    is_staff: user.is_staff,
  }))
}

export function getCurrentUserContext() {
  if (typeof window === 'undefined') return null
  return safeParse(localStorage.getItem(CURRENT_USER_STORAGE_KEY), null)
}

export function buildOwnerSnapshot() {
  const user = getCurrentUserContext()
  if (!user?.username && !user?.id) return null
  return {
    id: user.id,
    username: user.username,
    role: user.role,
    role_display: user.role_display,
    is_admin: user.is_admin,
    is_superuser: user.is_superuser,
    is_staff: user.is_staff,
  }
}

export function isAdminUser(user) {
  return Boolean(user?.is_admin || user?.is_superuser || user?.role === 'admin')
}

export function isOwnedByUser(item, user) {
  const owner = item?.owner || item?.payload?.owner || item?.resultData?.owner
  if (!owner) return false
  if (!user) return false
  if (user?.id !== undefined && owner.id !== undefined && String(owner.id) === String(user.id)) {
    return true
  }
  return Boolean(user?.username && owner.username && String(owner.username) === String(user.username))
}

export function canViewHistoryItem(item, user, options = {}) {
  if (!user) return false
  const owner = item?.owner || item?.payload?.owner || item?.resultData?.owner
  if (options.adminCanViewAll && isAdminUser(user)) {
    return true
  }
  if (!owner) {
    return Boolean(options.adminCanViewOwnerless && isAdminUser(user))
  }
  return isOwnedByUser(item, user)
}
