const DEFAULT_MIME = 'application/octet-stream'

const MIME_EXTENSION_MAP = {
  'application/json': 'json',
  'image/jpeg': 'jpg',
  'image/jpg': 'jpg',
  'image/png': 'png',
  'image/tiff': 'tif',
  'text/csv': 'csv',
  'text/plain': 'txt'
}

const MIME_DESCRIPTION_MAP = {
  'application/json': 'JSON 文件',
  'image/jpeg': 'JPEG 图片',
  'image/jpg': 'JPEG 图片',
  'image/png': 'PNG 图片',
  'image/tiff': 'TIFF 栅格',
  'text/csv': 'CSV 表格',
  'text/plain': '文本文件'
}

function getFilenameExtension(filename = '') {
  const match = String(filename).match(/\.([^.\\/:*?"<>|\s]+)$/)
  return match?.[1]?.toLowerCase() || ''
}

function getSavePickerTypes(filename, mimeType) {
  const normalizedMime = mimeType || DEFAULT_MIME
  const extension = getFilenameExtension(filename) || MIME_EXTENSION_MAP[normalizedMime] || ''

  if (!extension || normalizedMime === DEFAULT_MIME) {
    return []
  }

  return [{
    description: MIME_DESCRIPTION_MAP[normalizedMime] || '下载文件',
    accept: {
      [normalizedMime]: [`.${extension}`]
    }
  }]
}

function downloadBlobWithBrowser(blob, filename) {
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
}

export async function prepareFileSave(filename = 'download', mimeType = '') {
  const effectiveMimeType = mimeType || DEFAULT_MIME
  const suggestedName = String(filename || 'download')
  const pickerTypes = getSavePickerTypes(suggestedName, effectiveMimeType)

  if (window.showSaveFilePicker) {
    const handle = await window.showSaveFilePicker({
      suggestedName,
      ...(pickerTypes.length ? { types: pickerTypes } : {})
    })
    return {
      savedWithPicker: true,
      async write(blob) {
        const writable = await handle.createWritable()
        await writable.write(blob)
        await writable.close()
      }
    }
  }

  return {
    savedWithPicker: false,
    async write(blob) {
      downloadBlobWithBrowser(blob, suggestedName)
    }
  }
}

export async function saveBlobAsFile(blob, filename = 'download', mimeType = '') {
  const effectiveBlob = blob instanceof Blob
    ? blob
    : new Blob([blob], { type: mimeType || DEFAULT_MIME })
  const saveTarget = await prepareFileSave(filename, mimeType || effectiveBlob.type)
  await saveTarget.write(effectiveBlob)
  return { savedWithPicker: saveTarget.savedWithPicker }
}

export async function saveUrlAsFile(url, filename = 'download', mimeType = '') {
  if (!url) {
    throw new Error('暂无文件可下载')
  }

  const saveTarget = await prepareFileSave(filename, mimeType)
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const blob = await response.blob()
  await saveTarget.write(blob)
  return { savedWithPicker: saveTarget.savedWithPicker }
}
