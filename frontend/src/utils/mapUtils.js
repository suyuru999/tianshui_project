import TileLayer from 'ol/layer/Tile'
import ImageLayer from 'ol/layer/Image'
import VectorLayer from 'ol/layer/Vector'
import OSM from 'ol/source/OSM'
import XYZ from 'ol/source/XYZ'
import ImageWMS from 'ol/source/ImageWMS'
import TileWMS from 'ol/source/TileWMS'
import VectorSource from 'ol/source/Vector'
import KML from 'ol/format/KML'
import GeoJSON from 'ol/format/GeoJSON'
import { transform } from 'ol/proj'

// 天地图token（请替换为你自己的）
const TDT_TOKEN = '69874af7f35c741d7132c50f80acad29'

// 地图工具类
export class MapUtils {
  // 创建底图图层
  static createBaseMap(type) {
    switch (type) {
      case 'osm':
        return new TileLayer({
          source: new OSM(),
          visible: true
        })
      case 'tdt_vec': // 天地图标准矢量
        return new TileLayer({
          source: new XYZ({
            url: `https://t{0-7}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&FORMAT=tiles&TILEMATRIXSET=w&tk=${TDT_TOKEN}&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}`,
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      case 'tdt_img': // 天地图影像
        return new TileLayer({
          source: new XYZ({
            url: `https://t{0-7}.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&tk=${TDT_TOKEN}&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}`,
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      case 'tdt_ter': // 天地图地形
        return new TileLayer({
          source: new XYZ({
            url: `https://t{0-7}.tianditu.gov.cn/ter_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=ter&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&tk=${TDT_TOKEN}&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}`,
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      case 'tdt_gray': // 天地图灰色
        return new TileLayer({
          source: new XYZ({
            url: `https://t{0-7}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&FORMAT=tiles&TILEMATRIXSET=w&tk=${TDT_TOKEN}&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}`,
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      case 'satellite': // 兼容原有影像
        return new TileLayer({
          source: new XYZ({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      case 'terrain': // 兼容原有地形
        return new TileLayer({
          source: new XYZ({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      default:
        // 默认天地图标准矢量
        return new TileLayer({
          source: new XYZ({
            url: `https://t{0-7}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&FORMAT=tiles&TILEMATRIXSET=w&tk=${TDT_TOKEN}&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}`,
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
    }
  }

  // 加载KML文件
  static loadKML(url, options = {}) {
    const source = new VectorSource({
      url: url,
      format: new KML({
        extractStyles: options.extractStyles !== false
      })
    })

    return new VectorLayer({
      source: source,
      visible: options.visible !== false,
      style: options.style
    })
  }

  // 加载WMS服务
  static loadWMS(url, layers, options = {}) {
    const source = new TileWMS({
      url: url,
      params: {
        'LAYERS': layers,
        'TILED': true
      },
      serverType: options.serverType || 'geoserver',
      crossOrigin: 'anonymous'
    })

    return new TileLayer({
      source: source,
      visible: options.visible !== false
    })
  }

  // 加载WFS服务
  static loadWFS(url, typeName, options = {}) {
    const source = new VectorSource({
      format: new GeoJSON(),
      url: function(extent) {
        return url + '?' +
          'service=WFS&' +
          'version=1.0.0&' +
          'request=GetFeature&' +
          'typeName=' + typeName + '&' +
          'maxFeatures=50&' +
          'outputFormat=application/json&' +
          'srsname=EPSG:3857&' +
          'bbox=' + extent.join(',') + ',EPSG:3857'
      },
      strategy: options.strategy
    })

    return new VectorLayer({
      source: source,
      visible: options.visible !== false,
      style: options.style
    })
  }

  // 加载GeoJSON数据
  static loadGeoJSON(data, options = {}) {
    const source = new VectorSource({
      features: new GeoJSON().readFeatures(data, {
        featureProjection: 'EPSG:3857'
      })
    })

    return new VectorLayer({
      source: source,
      visible: options.visible !== false,
      style: options.style
    })
  }

  // 从本地文件加载数据
  static loadFromFile(file, options = {}) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      
      reader.onload = (event) => {
        try {
          let layer
          const content = event.target.result
          
          if (file.name.toLowerCase().endsWith('.kml')) {
            layer = this.loadKML(content, options)
          } else if (file.name.toLowerCase().endsWith('.geojson') || file.name.toLowerCase().endsWith('.json')) {
            const data = JSON.parse(content)
            layer = this.loadGeoJSON(data, options)
          } else {
            reject(new Error('不支持的文件格式'))
            return
          }
          
          resolve(layer)
        } catch (error) {
          reject(error)
        }
      }
      
      reader.onerror = () => {
        reject(new Error('文件读取失败'))
      }
      
      if (file.name.toLowerCase().endsWith('.kml')) {
        reader.readAsText(file)
      } else {
        reader.readAsText(file)
      }
    })
  }

  // 坐标转换
  static transformCoordinates(coordinates, fromProjection, toProjection) {
    return transform(coordinates, fromProjection, toProjection)
  }

  // 获取图层范围
  static getLayerExtent(layer) {
    const source = layer.getSource()
    if (source.getExtent) {
      return source.getExtent()
    }
    return null
  }

  // 缩放到图层
  static zoomToLayer(map, layer) {
    const extent = this.getLayerExtent(layer)
    if (extent) {
      map.getView().fit(extent, {
        padding: [50, 50, 50, 50],
        duration: 1000
      })
    }
  }
} 