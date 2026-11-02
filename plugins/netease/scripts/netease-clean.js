// 网易云音乐 JSON 广告字段清理（原创实现；不复制上游脚本）
// 目标：删除响应里的广告标记字段与带非空广告标记的卡片，保留内容字段。
(function () {
  var AD_KEYS = {
    ad: 1, adid: 1, adurl: 1, adurlV2: 1, adSource: 1, adLocation: 1,
    adInfo: 1, adData: 1, adList: 1, adConfig: 1, adType: 1, isAd: 1,
    adResource: 1, monitorImpress: 1, monitorClick: 1, monitorType: 1,
    monitorImpressList: 1, monitorClickList: 1, monitorBlackList: 1,
    extMonitor: 1, extMonitorInfo: 1
  };
  var AD_MARKERS = ["adid", "adurl", "adurlV2", "adSource", "adLocation", "adResource"];

  function isAdCard(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    for (var i = 0; i < AD_MARKERS.length; i++) {
      var v = value[AD_MARKERS[i]];
      if (v !== undefined && v !== null && v !== "" && v !== 0) return true;
    }
    return false;
  }

  function clean(value) {
    if (Array.isArray(value)) {
      var out = [];
      for (var i = 0; i < value.length; i++) {
        if (isAdCard(value[i])) continue;
        out.push(clean(value[i]));
      }
      return out;
    }
    if (value && typeof value === "object") {
      for (var key in value) {
        if (!Object.prototype.hasOwnProperty.call(value, key)) continue;
        if (AD_KEYS[key]) {
          delete value[key];
        } else {
          value[key] = clean(value[key]);
        }
      }
    }
    return value;
  }

  try {
    if (typeof $response !== "undefined" && $response.body) {
      var body = $response.body;
      if (typeof body !== "string") body = String(body);
      var data = JSON.parse(body);
      var cleaned = clean(data);
      $done({ body: JSON.stringify(cleaned) });
    } else {
      $done({});
    }
  } catch (e) {
    $done({});
  }
})();
