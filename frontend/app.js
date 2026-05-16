const map = L.map("map", { zoomControl: true }).setView([30.59, 114.3], 11);

// 高德 API 返回 GCJ-02 坐标，使用高德瓦片避免路线和底图偏移。
L.tileLayer("https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}", {
  subdomains: ["1", "2", "3", "4"],
  maxZoom: 19,
  attribution: "&copy; 高德地图",
}).addTo(map);

const state = {
  destinations: [],
  destinationMarkers: [],
  recommendationMarkers: [],
  routeLayers: [],
  routeSegmentLayers: [],
  lastRecommendation: null,
  currentItinerary: null,
  selectedCompareIds: new Set(),
};

const destinationIcon = L.divIcon({ className: "destination-marker", iconSize: [18, 18] });
const poiIcon = L.divIcon({ className: "poi-marker", iconSize: [17, 17] });
const gridIcon = L.divIcon({ className: "grid-marker", iconSize: [34, 34] });

const searchInput = document.querySelector("#searchInput");
const provinceSelect = document.querySelector("#provinceSelect");
const citySelect = document.querySelector("#citySelect");
const searchBtn = document.querySelector("#searchBtn");
const searchResults = document.querySelector("#searchResults");
const agentInput = document.querySelector("#agentInput");
const agentBtn = document.querySelector("#agentBtn");
const agentOutput = document.querySelector("#agentOutput");
const agentStatus = document.querySelector("#agentStatus");
const destinationsEl = document.querySelector("#destinations");
const destinationCount = document.querySelector("#destinationCount");
const recommendBtn = document.querySelector("#recommendBtn");
const recommendationsEl = document.querySelector("#recommendations");
const statusText = document.querySelector("#statusText");
const routeModeSelect = document.querySelector("#routeModeSelect");
const preferenceSelect = document.querySelector("#preferenceSelect");
const lessWalkingInput = document.querySelector("#lessWalkingInput");
const lessTransfersInput = document.querySelector("#lessTransfersInput");
const familyFriendlyInput = document.querySelector("#familyFriendlyInput");
const elderFriendlyInput = document.querySelector("#elderFriendlyInput");
const hotelLimitInput = document.querySelector("#hotelLimitInput");
const avgTimeWeight = document.querySelector("#avgTimeWeight");
const maxTimeWeight = document.querySelector("#maxTimeWeight");
const comfortWeight = document.querySelector("#comfortWeight");
const avgTimeWeightValue = document.querySelector("#avgTimeWeightValue");
const maxTimeWeightValue = document.querySelector("#maxTimeWeightValue");
const comfortWeightValue = document.querySelector("#comfortWeightValue");
const startTimeInput = document.querySelector("#startTimeInput");
const stayMinutesInput = document.querySelector("#stayMinutesInput");
const returnToHotelInput = document.querySelector("#returnToHotelInput");
const savePlanBtn = document.querySelector("#savePlanBtn");
const shareOutput = document.querySelector("#shareOutput");
const comparisonEl = document.querySelector("#comparison");
const itineraryWorkspace = document.querySelector("#itineraryWorkspace");
const itineraryPanel = document.querySelector("#itineraryPanel");
const recommendPrevBtn = document.querySelector("#recommendPrevBtn");
const recommendNextBtn = document.querySelector("#recommendNextBtn");
const mapCard = document.querySelector(".map-card");
const mapMiniBtn = document.querySelector("#mapMiniBtn");
const feedbackOpenBtn = document.querySelector("#feedbackOpenBtn");
const feedbackModal = document.querySelector("#feedbackModal");
const feedbackCloseBtn = document.querySelector("#feedbackCloseBtn");
const feedbackCancelBtn = document.querySelector("#feedbackCancelBtn");
const feedbackSubmitBtn = document.querySelector("#feedbackSubmitBtn");
const feedbackRating = document.querySelector("#feedbackRating");
const feedbackComment = document.querySelector("#feedbackComment");
const feedbackMessage = document.querySelector("#feedbackMessage");

const weightPresets = {
  balanced: { avgTime: 50, maxTime: 30, comfort: 20 },
  time: { avgTime: 65, maxTime: 25, comfort: 10 },
  comfort: { avgTime: 35, maxTime: 20, comfort: 45 },
};

const provinceCityMap = {
  "全国": [{ label: "全国", value: "" }],
  "北京市": ["北京"],
  "天津市": ["天津"],
  "河北省": ["石家庄", "唐山", "秦皇岛", "邯郸", "邢台", "保定", "张家口", "承德", "沧州", "廊坊", "衡水"],
  "山西省": ["太原", "大同", "阳泉", "长治", "晋城", "朔州", "晋中", "运城", "忻州", "临汾", "吕梁"],
  "内蒙古自治区": ["呼和浩特", "包头", "乌海", "赤峰", "通辽", "鄂尔多斯", "呼伦贝尔", "巴彦淖尔", "乌兰察布", "兴安盟", "锡林郭勒盟", "阿拉善盟"],
  "辽宁省": ["沈阳", "大连", "鞍山", "抚顺", "本溪", "丹东", "锦州", "营口", "阜新", "辽阳", "盘锦", "铁岭", "朝阳", "葫芦岛"],
  "吉林省": ["长春", "吉林", "四平", "辽源", "通化", "白山", "松原", "白城", "延边"],
  "黑龙江省": ["哈尔滨", "齐齐哈尔", "鸡西", "鹤岗", "双鸭山", "大庆", "伊春", "佳木斯", "七台河", "牡丹江", "黑河", "绥化", "大兴安岭"],
  "上海市": ["上海"],
  "江苏省": ["南京", "无锡", "徐州", "常州", "苏州", "南通", "连云港", "淮安", "盐城", "扬州", "镇江", "泰州", "宿迁"],
  "浙江省": ["杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水"],
  "安徽省": ["合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵", "安庆", "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "池州", "宣城"],
  "福建省": ["福州", "厦门", "莆田", "三明", "泉州", "漳州", "南平", "龙岩", "宁德"],
  "江西省": ["南昌", "景德镇", "萍乡", "九江", "新余", "鹰潭", "赣州", "吉安", "宜春", "抚州", "上饶"],
  "山东省": ["济南", "青岛", "淄博", "枣庄", "东营", "烟台", "潍坊", "济宁", "泰安", "威海", "日照", "临沂", "德州", "聊城", "滨州", "菏泽"],
  "河南省": ["郑州", "开封", "洛阳", "平顶山", "安阳", "鹤壁", "新乡", "焦作", "濮阳", "许昌", "漯河", "三门峡", "南阳", "商丘", "信阳", "周口", "驻马店", "济源"],
  "湖北省": ["武汉", "黄石", "十堰", "宜昌", "襄阳", "鄂州", "荆门", "孝感", "荆州", "黄冈", "咸宁", "随州", "恩施", "仙桃", "潜江", "天门", "神农架"],
  "湖南省": ["长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德", "张家界", "益阳", "郴州", "永州", "怀化", "娄底", "湘西"],
  "广东省": ["广州", "深圳", "珠海", "汕头", "佛山", "韶关", "湛江", "肇庆", "江门", "茂名", "惠州", "梅州", "汕尾", "河源", "阳江", "清远", "东莞", "中山", "潮州", "揭阳", "云浮"],
  "广西壮族自治区": ["南宁", "柳州", "桂林", "梧州", "北海", "防城港", "钦州", "贵港", "玉林", "百色", "贺州", "河池", "来宾", "崇左"],
  "海南省": ["海口", "三亚", "三沙", "儋州", "五指山", "琼海", "文昌", "万宁", "东方", "定安", "屯昌", "澄迈", "临高", "白沙", "昌江", "乐东", "陵水", "保亭", "琼中"],
  "重庆市": ["重庆"],
  "四川省": ["成都", "自贡", "攀枝花", "泸州", "德阳", "绵阳", "广元", "遂宁", "内江", "乐山", "南充", "眉山", "宜宾", "广安", "达州", "雅安", "巴中", "资阳", "阿坝", "甘孜", "凉山"],
  "贵州省": ["贵阳", "六盘水", "遵义", "安顺", "毕节", "铜仁", "黔西南", "黔东南", "黔南"],
  "云南省": ["昆明", "曲靖", "玉溪", "保山", "昭通", "丽江", "普洱", "临沧", "楚雄", "红河", "文山", "西双版纳", "大理", "德宏", "怒江", "迪庆"],
  "西藏自治区": ["拉萨", "日喀则", "昌都", "林芝", "山南", "那曲", "阿里"],
  "陕西省": ["西安", "铜川", "宝鸡", "咸阳", "渭南", "延安", "汉中", "榆林", "安康", "商洛"],
  "甘肃省": ["兰州", "嘉峪关", "金昌", "白银", "天水", "武威", "张掖", "平凉", "酒泉", "庆阳", "定西", "陇南", "临夏", "甘南"],
  "青海省": ["西宁", "海东", "海北", "黄南", "海南", "果洛", "玉树", "海西"],
  "宁夏回族自治区": ["银川", "石嘴山", "吴忠", "固原", "中卫"],
  "新疆维吾尔自治区": ["乌鲁木齐", "克拉玛依", "吐鲁番", "哈密", "昌吉", "博尔塔拉", "巴音郭楞", "阿克苏", "克孜勒苏", "喀什", "和田", "伊犁", "塔城", "阿勒泰", "石河子", "阿拉尔", "图木舒克", "五家渠", "北屯", "铁门关", "双河", "可克达拉", "昆玉", "胡杨河", "新星", "白杨"],
  "香港特别行政区": ["香港"],
  "澳门特别行政区": ["澳门"],
  "台湾省": ["台北", "高雄", "台中", "台南", "新北", "桃园", "基隆", "新竹", "嘉义"]
};

let searchTimer = null;
let searchRequestId = 0;
let miniMapDrag = null;
let selectedFeedbackRating = 0;
let currentAgentStatus = "";
const feedbackSubmittedKey = "smartTravelFeedbackSubmitted";
let pendingExitFeedback = false;

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

function setStatus(text) {
  statusText.textContent = text;
}

function getWeights() {
  return {
    avgTime: Number(avgTimeWeight.value || 0),
    maxTime: Number(maxTimeWeight.value || 0),
    comfort: Number(comfortWeight.value || 0),
  };
}

function getTravelPreferences() {
  return {
    lessWalking: lessWalkingInput.checked,
    lessTransfers: lessTransfersInput.checked,
    familyFriendly: familyFriendlyInput.checked,
    elderFriendly: elderFriendlyInput.checked,
  };
}

function applyTravelPreferences(preferences = {}) {
  lessWalkingInput.checked = Boolean(preferences.lessWalking);
  lessTransfersInput.checked = Boolean(preferences.lessTransfers);
  familyFriendlyInput.checked = Boolean(preferences.familyFriendly);
  elderFriendlyInput.checked = Boolean(preferences.elderFriendly);
}

function syncWeightLabels() {
  avgTimeWeightValue.textContent = `${avgTimeWeight.value}%`;
  maxTimeWeightValue.textContent = `${maxTimeWeight.value}%`;
  comfortWeightValue.textContent = `${comfortWeight.value}%`;
}

function applyWeightPreset(name) {
  const preset = weightPresets[name] || weightPresets.balanced;
  avgTimeWeight.value = preset.avgTime;
  maxTimeWeight.value = preset.maxTime;
  comfortWeight.value = preset.comfort;
  syncWeightLabels();
}

function clearRecommendationMarkers() {
  state.recommendationMarkers.forEach((marker) => marker.remove());
  state.recommendationMarkers = [];
  clearRouteLayers();
}

function clearRouteLayers() {
  state.routeLayers.forEach((layer) => layer.remove());
  state.routeLayers = [];
  state.routeSegmentLayers = [];
}

const routePalette = ["#4666F5", "#14B8A6", "#F59E0B", "#A855F7", "#EF4444", "#06B6D4", "#84CC16"];

function focusRouteSegment(index) {
  state.routeSegmentLayers.forEach((layer, layerIndex) => {
    const color = routePalette[layerIndex % routePalette.length];
    layer.setStyle({
      color,
      opacity: layerIndex === index ? 0.95 : 0.18,
      weight: layerIndex === index ? 7 : 4,
    });
    if (layerIndex === index) {
      layer.bringToFront();
      map.fitBounds(layer.getBounds(), { padding: [72, 72] });
    }
  });
  itineraryPanel.querySelectorAll(".segment-card").forEach((card, cardIndex) => {
    card.classList.toggle("active", cardIndex === index);
  });
}

function renderDestinations() {
  destinationCount.textContent = state.destinations.length;
  state.destinationMarkers.forEach((marker) => marker.remove());
  state.destinationMarkers = [];

  if (state.destinations.length === 0) {
    destinationsEl.className = "destination-tags empty-state";
    destinationsEl.textContent = "在地图上点击或搜索添加目的地";
    return;
  }

  destinationsEl.className = "destination-tags";
  destinationsEl.innerHTML = "";
  state.destinations.forEach((dest, index) => {
    const marker = L.marker([dest.lat, dest.lon], { icon: destinationIcon })
      .addTo(map)
      .bindPopup(dest.name);
    state.destinationMarkers.push(marker);

    const item = document.createElement("div");
    item.className = "destination-item";
    item.innerHTML = `
      <div>
        <strong>${escapeHtml(dest.name)}</strong>
        <div class="item-meta">${dest.lon.toFixed(5)}, ${dest.lat.toFixed(5)}</div>
      </div>
      <input class="input-control" type="number" min="0.1" step="0.1" value="${dest.weight}" title="目的地权重" />
      <button class="icon-btn" title="删除目的地">×</button>
    `;
    item.querySelector("input").addEventListener("input", (event) => {
      state.destinations[index].weight = Number(event.target.value || 1);
    });
    item.querySelector("button").addEventListener("click", () => {
      state.destinations.splice(index, 1);
      renderDestinations();
    });
    destinationsEl.appendChild(item);
  });
}

function addDestination(destination) {
  state.destinations.push({
    name: destination.name || `目的地 ${state.destinations.length + 1}`,
    lon: Number(destination.lon),
    lat: Number(destination.lat),
    weight: destination.weight || 1,
  });
  renderDestinations();
}

function setDestinations(destinations) {
  state.destinations = (destinations || []).map((destination, index) => ({
    name: destination.name || `目的地 ${index + 1}`,
    lon: Number(destination.lon),
    lat: Number(destination.lat),
    weight: destination.weight || 1,
  }));
  renderDestinations();
}

async function warmStatus() {
  setStatus("检查 Key");
  try {
    const status = await api("/api/status");
    setStatus(status.hasKey ? `高德 API 已配置` : "缺少 AMAP_KEY");
    currentAgentStatus = status.hasMimoKey ? "MiMo" : (status.hasDoubaoKey ? "豆包" : (status.hasAgentKey ? "OpenAI" : "规则回退"));
    agentStatus.textContent = currentAgentStatus;
  } catch (error) {
    setStatus("状态异常");
    recommendationsEl.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

function normalizeCityOptions(items) {
  return items.map((item) => {
    if (typeof item === "string") return { label: item, value: item };
    return item;
  });
}

function populateProvinceSelect(selectedProvince = "湖北省") {
  provinceSelect.innerHTML = "";
  Object.keys(provinceCityMap).forEach((province) => {
    const option = document.createElement("option");
    option.value = province;
    option.textContent = province;
    provinceSelect.appendChild(option);
  });
  provinceSelect.value = provinceCityMap[selectedProvince] ? selectedProvince : "湖北省";
  populateCitySelect();
}

function populateCitySelect(selectedCity = "") {
  const cities = normalizeCityOptions(provinceCityMap[provinceSelect.value] || provinceCityMap["全国"]);
  citySelect.innerHTML = "";
  cities.forEach((city) => {
    const option = document.createElement("option");
    option.value = city.value;
    option.textContent = city.label;
    citySelect.appendChild(option);
  });
  const matched = cities.some((city) => city.value === selectedCity);
  citySelect.value = matched ? selectedCity : cities[0].value;
}

function currentSettings() {
  return {
    province: provinceSelect.value,
    city: citySelect.value,
    routeMode: routeModeSelect.value,
    preference: preferenceSelect.value,
    weights: getWeights(),
    travelPreferences: getTravelPreferences(),
    hotelLimit: Number(hotelLimitInput.value || 12),
    startTime: startTimeInput.value || "09:00",
    stayMinutes: Number(stayMinutesInput.value || 60),
    returnToHotel: returnToHotelInput.checked,
  };
}

function applySettings(settings = {}) {
  if (settings.province && provinceCityMap[settings.province]) {
    provinceSelect.value = settings.province;
    populateCitySelect(settings.city || "");
  } else if (typeof settings.city === "string") {
    const matchedProvince = Object.entries(provinceCityMap).find(([, cities]) =>
      normalizeCityOptions(cities).some((city) => city.value === settings.city)
    );
    if (matchedProvince) {
      provinceSelect.value = matchedProvince[0];
      populateCitySelect(settings.city);
    }
  }
  if (typeof settings.city === "string") {
    const hasCity = Array.from(citySelect.options).some((option) => option.value === settings.city);
    if (hasCity) citySelect.value = settings.city;
  }
  const routeMode = settings.routeMode === "transit" ? "transit" : "driving";
  routeModeSelect.value = routeMode;
  if (settings.preference && preferenceSelect.querySelector(`option[value="${settings.preference}"]`)) {
    preferenceSelect.value = settings.preference;
  }
  if (settings.weights) {
    avgTimeWeight.value = settings.weights.avgTime ?? avgTimeWeight.value;
    maxTimeWeight.value = settings.weights.maxTime ?? maxTimeWeight.value;
    comfortWeight.value = settings.weights.comfort ?? comfortWeight.value;
    syncWeightLabels();
  }
  if (settings.travelPreferences) applyTravelPreferences(settings.travelPreferences);
  if (settings.hotelLimit) hotelLimitInput.value = settings.hotelLimit;
  if (settings.startTime) startTimeInput.value = settings.startTime;
  if (settings.stayMinutes) stayMinutesInput.value = settings.stayMinutes;
  if (typeof settings.returnToHotel === "boolean") returnToHotelInput.checked = settings.returnToHotel;
}

function buildPlanSnapshot() {
  return {
    version: 1,
    savedAt: new Date().toISOString(),
    destinations: state.destinations,
    settings: currentSettings(),
    recommendation: state.lastRecommendation,
    itinerary: state.currentItinerary,
  };
}

async function savePlan() {
  if (!state.lastRecommendation) {
    shareOutput.textContent = "请先计算酒店推荐。";
    return;
  }
  savePlanBtn.disabled = true;
  savePlanBtn.textContent = "保存中...";
  try {
    const data = await api("/api/plans", {
      method: "POST",
      body: JSON.stringify({
        title: state.destinations.map((item) => item.name).join("、") || "旅行方案",
        payload: buildPlanSnapshot(),
      }),
    });
    const url = new URL(data.url, window.location.origin).toString();
    shareOutput.innerHTML = `<a href="${escapeHtml(url)}">${escapeHtml(url)}</a>`;
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(url).catch(() => {});
    }
  } catch (error) {
    shareOutput.textContent = error.message;
  } finally {
    savePlanBtn.disabled = false;
    savePlanBtn.textContent = "保存方案";
  }
}

async function restorePlanFromUrl() {
  const planId = new URLSearchParams(window.location.search).get("plan");
  if (!planId) return;
  setStatus("读取分享方案");
  try {
    const data = await api(`/api/plans?id=${encodeURIComponent(planId)}`);
    const payload = data.payload || {};
    setDestinations(payload.destinations || []);
    applySettings(payload.settings || {});
    state.lastRecommendation = payload.recommendation || null;
    state.currentItinerary = payload.itinerary || null;
    state.selectedCompareIds.clear();
    if (state.lastRecommendation) {
      renderRecommendations(state.lastRecommendation);
      if (state.currentItinerary) {
        renderItinerary(state.currentItinerary);
      }
      shareOutput.textContent = "已恢复分享方案。";
      setStatus("已恢复");
    }
  } catch (error) {
    setStatus("恢复失败");
    shareOutput.textContent = error.message;
  }
}

async function searchPois(options = {}) {
  const q = searchInput.value.trim();
  if (!q) {
    searchResults.innerHTML = "";
    return;
  }
  if (q.length < 2 && !options.force) {
    searchResults.innerHTML = `<div class="empty">继续输入以检索目的地</div>`;
    return;
  }
  const requestId = ++searchRequestId;
  const city = citySelect.value;
  searchResults.innerHTML = `<div class="empty">正在搜索目的地...</div>`;
  try {
    const cityQuery = city ? `&city=${encodeURIComponent(city)}` : "";
    const data = await api(`/api/pois/search?q=${encodeURIComponent(q)}${cityQuery}`);
    if (requestId !== searchRequestId) return;
    if (data.items.length === 0) {
      searchResults.innerHTML = `<div class="empty">没有找到匹配地点</div>`;
      return;
    }
    searchResults.innerHTML = "";
    data.items.forEach((poi) => {
      const item = document.createElement("div");
      item.className = "result-item";
      item.innerHTML = `
        <div class="item-title"><strong>${escapeHtml(poi.name)}</strong></div>
        <div class="item-meta">${escapeHtml(poi.type || poi.address || "")}</div>
      `;
      item.addEventListener("click", () => {
        addDestination(poi);
        map.setView([poi.lat, poi.lon], 14);
        searchResults.innerHTML = "";
      });
      searchResults.appendChild(item);
    });
  } catch (error) {
    if (requestId !== searchRequestId) return;
    searchResults.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

function schedulePoiSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    searchPois();
  }, 360);
}

function scrollRecommendationCards(direction) {
  const firstCard = recommendationsEl.querySelector(".recommendation");
  const cardWidth = firstCard ? firstCard.getBoundingClientRect().width : 380;
  recommendationsEl.scrollBy({
    left: direction * (cardWidth + 24),
    behavior: "smooth",
  });
}

function toggleMiniMap() {
  const isMini = mapCard.classList.toggle("is-mini");
  mapMiniBtn.setAttribute("aria-pressed", String(isMini));
  mapMiniBtn.textContent = isMini ? "恢复地图" : "小窗地图";
  if (isMini) {
    mapCard.style.left = "";
    mapCard.style.top = "";
    mapCard.style.right = "22px";
    mapCard.style.bottom = "22px";
  } else {
    mapCard.style.left = "";
    mapCard.style.top = "";
    mapCard.style.right = "";
    mapCard.style.bottom = "";
  }
  setTimeout(() => map.invalidateSize(), 180);
}

function openFeedbackModal() {
  feedbackModal.classList.remove("hidden");
  feedbackMessage.textContent = "";
  feedbackMessage.className = "feedback-message";
  feedbackComment.focus();
}

function closeFeedbackModal() {
  feedbackModal.classList.add("hidden");
}

function setFeedbackRating(rating) {
  selectedFeedbackRating = rating;
  feedbackRating.querySelectorAll(".rating-btn").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.rating) === rating);
  });
}

function hasSubmittedFeedback() {
  try {
    return localStorage.getItem(feedbackSubmittedKey) === "1";
  } catch (error) {
    return false;
  }
}

function markFeedbackSubmitted() {
  try {
    localStorage.setItem(feedbackSubmittedKey, "1");
  } catch (error) {
    // Ignore storage errors; the feedback itself has already been saved server-side.
  }
}

function feedbackContext() {
  return {
    url: window.location.href,
    userAgent: navigator.userAgent,
    agentStatus: currentAgentStatus || agentStatus.textContent,
    destinations: state.destinations,
    settings: currentSettings(),
    hasRecommendation: Boolean(state.lastRecommendation),
    recommendationCount: ((state.lastRecommendation || {}).poiRecommendations || []).length,
    hasItinerary: Boolean(state.currentItinerary),
    itinerarySummary: state.currentItinerary
      ? {
          routeMode: state.currentItinerary.routeMode,
          totalTravelMinutes: state.currentItinerary.totalTravelMinutes,
          totalKilometers: state.currentItinerary.totalKilometers,
          endTime: state.currentItinerary.endTime,
        }
      : null,
  };
}

async function submitFeedback() {
  const comment = feedbackComment.value.trim();
  feedbackMessage.className = "feedback-message";
  if (!selectedFeedbackRating) {
    feedbackMessage.classList.add("error");
    feedbackMessage.textContent = "请选择 1-5 分满意度。";
    return;
  }
  if (!comment) {
    feedbackMessage.classList.add("error");
    feedbackMessage.textContent = "请填写反馈内容。";
    return;
  }
  feedbackSubmitBtn.disabled = true;
  feedbackSubmitBtn.textContent = "提交中...";
  try {
    await api("/api/feedback", {
      method: "POST",
      body: JSON.stringify({
        rating: selectedFeedbackRating,
        comment,
        context: feedbackContext(),
      }),
    });
    markFeedbackSubmitted();
    feedbackMessage.classList.add("success");
    feedbackMessage.textContent = "感谢反馈，已保存。";
    feedbackComment.value = "";
    setFeedbackRating(0);
    setTimeout(closeFeedbackModal, 700);
  } catch (error) {
    feedbackMessage.classList.add("error");
    feedbackMessage.textContent = error.message;
  } finally {
    feedbackSubmitBtn.disabled = false;
    feedbackSubmitBtn.textContent = "提交反馈";
  }
}

function startMiniMapDrag(event) {
  if (!mapCard.classList.contains("is-mini")) return;
  if (event.target.closest(".leaflet-control") || event.target.closest(".map-pin-btn")) return;
  const pointer = event.touches ? event.touches[0] : event;
  const rect = mapCard.getBoundingClientRect();
  miniMapDrag = {
    offsetX: pointer.clientX - rect.left,
    offsetY: pointer.clientY - rect.top,
  };
  mapCard.classList.add("is-dragging");
  document.addEventListener("mousemove", dragMiniMap);
  document.addEventListener("mouseup", stopMiniMapDrag);
  document.addEventListener("touchmove", dragMiniMap, { passive: false });
  document.addEventListener("touchend", stopMiniMapDrag);
}

function dragMiniMap(event) {
  if (!miniMapDrag) return;
  if (event.cancelable) event.preventDefault();
  const pointer = event.touches ? event.touches[0] : event;
  const maxLeft = window.innerWidth - mapCard.offsetWidth - 8;
  const maxTop = window.innerHeight - mapCard.offsetHeight - 8;
  const left = Math.max(8, Math.min(maxLeft, pointer.clientX - miniMapDrag.offsetX));
  const top = Math.max(8, Math.min(maxTop, pointer.clientY - miniMapDrag.offsetY));
  mapCard.style.left = `${left}px`;
  mapCard.style.top = `${top}px`;
  mapCard.style.right = "auto";
  mapCard.style.bottom = "auto";
}

function stopMiniMapDrag() {
  if (!miniMapDrag) return;
  miniMapDrag = null;
  mapCard.classList.remove("is-dragging");
  document.removeEventListener("mousemove", dragMiniMap);
  document.removeEventListener("mouseup", stopMiniMapDrag);
  document.removeEventListener("touchmove", dragMiniMap);
  document.removeEventListener("touchend", stopMiniMapDrag);
  setTimeout(() => map.invalidateSize(), 80);
}

async function runAgent() {
  const message = agentInput.value.trim();
  if (!message) {
    agentOutput.innerHTML = `<div class="empty">请先输入你的旅行需求。</div>`;
    return;
  }
  agentBtn.disabled = true;
  agentBtn.textContent = "AI 正在规划...";
  agentOutput.innerHTML = `<div class="empty">正在理解需求、搜索目的地、推荐酒店并生成路线...</div>`;
  clearRecommendationMarkers();
  try {
    const data = await api("/api/agent", {
      method: "POST",
      body: JSON.stringify({ message, city: citySelect.value }),
    });
    if (data.needsConfirmation) {
      agentOutput.innerHTML = `<div class="empty">${escapeHtml(data.message)}</div>`;
      return;
    }
    setDestinations(data.destinations || []);
    renderAgentResult(data);
    state.lastRecommendation = data.recommendation;
    renderRecommendations(data.recommendation);
    const firstCard = recommendationsEl.querySelector(".recommendation");
    if (firstCard && data.itinerary) {
      renderItinerary(data.itinerary);
      state.currentItinerary = data.itinerary;
    }
  } catch (error) {
    agentOutput.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  } finally {
    agentBtn.disabled = false;
    agentBtn.textContent = "AI 生成方案";
  }
}

function renderAgentResult(data) {
  const parsed = data.parsed || {};
  const destinations = (data.destinations || []).map((item) => escapeHtml(item.name)).join("、");
  const parserName = parsed.parser === "mimo" ? "MiMo Agent" : (parsed.parser === "doubao" ? "豆包 Agent" : (parsed.parser === "openai" ? "OpenAI Agent" : "本地规则 Agent"));
  agentOutput.innerHTML = `
    <div class="insight-box">
      <strong>${parserName} 已生成方案</strong>
      ${escapeHtml(data.message || "已完成推荐。")}
      <div class="details">识别目的地：${destinations || "未识别"}</div>
      <div class="details">出行方式：${escapeHtml(parsed.routeMode || "driving")}；出发时间：${escapeHtml(parsed.startTime || "09:00")}</div>
    </div>
  `;
  if (parsed.weights) {
    avgTimeWeight.value = parsed.weights.avgTime ?? avgTimeWeight.value;
    maxTimeWeight.value = parsed.weights.maxTime ?? maxTimeWeight.value;
    comfortWeight.value = parsed.weights.comfort ?? comfortWeight.value;
    syncWeightLabels();
  }
  if (parsed.travelPreferences) applyTravelPreferences(parsed.travelPreferences);
  routeModeSelect.value = parsed.routeMode === "transit" ? "transit" : "driving";
  if (parsed.startTime) startTimeInput.value = parsed.startTime;
  if (parsed.stayMinutes) stayMinutesInput.value = Math.round(parsed.stayMinutes);
}

async function recommend() {
  if (state.destinations.length === 0) {
    recommendationsEl.innerHTML = `<div class="empty">请先添加至少一个目的地</div>`;
    return;
  }

  clearRecommendationMarkers();
  setStatus("计算中");
  recommendationsEl.innerHTML = `<div class="empty">正在计算酒店到各目的地的通勤成本...</div>`;

  try {
    const data = await api("/api/recommend", {
      method: "POST",
      body: JSON.stringify({
        destinations: state.destinations,
        city: citySelect.value,
        routeMode: routeModeSelect.value,
        preference: preferenceSelect.value,
        weights: getWeights(),
        travelPreferences: getTravelPreferences(),
        hotelLimit: Number(hotelLimitInput.value || 12),
      }),
    });
    setStatus("完成");
    state.lastRecommendation = data;
    state.currentItinerary = null;
    state.selectedCompareIds.clear();
    renderRecommendations(data);
  } catch (error) {
    setStatus("失败");
    recommendationsEl.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

function renderRecommendations(data) {
  state.lastRecommendation = data;
  const poiItems = data.poiRecommendations || [];
  if (poiItems.length === 0) {
    recommendationsEl.innerHTML = `<div class="empty">没有找到可达酒店推荐</div>`;
    renderComparison();
    return;
  }

  recommendationsEl.innerHTML = "";
  poiItems.forEach((item, index) => renderRecommendation(item, index + 1));
  renderComparison();

  const group = L.featureGroup([...state.destinationMarkers, ...state.recommendationMarkers]);
  if (group.getLayers().length > 0) {
    map.fitBounds(group.getBounds(), { padding: [48, 48] });
  }
}

function renderRecommendation(item, rank) {
  const card = document.createElement("article");
  card.className = "recommendation";
  const compareId = item.id || `${item.name}-${item.lon}-${item.lat}`;
  card.dataset.compareId = compareId;
  const imageClass = rank % 3 === 2 ? "hotel-image alt-2" : (rank % 3 === 0 ? "hotel-image alt-3" : "hotel-image");
  const modeSummary = [
    item.drivingAvgMinutes ? `驾车均值 ${item.drivingAvgMinutes} 分` : "",
    item.transitAvgMinutes ? `公交均值 ${item.transitAvgMinutes} 分` : "",
    item.walkingAvgKilometers ? `平均步行 ${item.walkingAvgKilometers} km` : "",
    item.transferAvgCount !== null && item.transferAvgCount !== undefined ? `平均换乘 ${item.transferAvgCount} 次` : "",
  ].filter(Boolean).join(" · ");
  const marketSummary = [
    item.rating ? `评分 ${Number(item.rating).toFixed(1)}/5` : "",
    item.price ? `参考价 ${Math.round(Number(item.price))}${escapeHtml(item.priceUnit || "元")}` : "",
    item.valueScore ? `性价比 ${item.valueScore}` : "价格缺失，不参与性价比",
    item.marketDataSource ? `来源 ${escapeHtml(item.marketDataSource)}` : "",
  ].filter(Boolean).join(" · ");

  card.innerHTML = `
    <div class="${imageClass}">
      <span class="rank-badge">TOP ${rank}</span>
    </div>
    <div class="recommendation-body">
      <div class="item-title">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="score">${item.score}<small>综合评分</small></span>
      </div>
      <div class="item-meta">${escapeHtml(item.type || "酒店")} ${item.address ? ` · ${escapeHtml(item.address)}` : ""}</div>
      <div class="metrics">
        <div class="metric"><span>均时</span> <strong>${item.avgMinutes}m</strong></div>
        <div class="metric"><span>最远</span> <strong>${item.maxMinutes}m</strong></div>
        <div class="metric"><span>舒适</span> <strong>${item.comfortScore}</strong></div>
        <div class="metric"><span>偏好</span> <strong>${item.preferenceFitScore ?? "未启用"}</strong></div>
      </div>
      ${marketSummary ? `<div class="market-data">${marketSummary}</div>` : ""}
      <div class="details">${escapeHtml(modeSummary || "按当前路线方式计算")}</div>
      <div class="details">${escapeHtml(item.explanation)}</div>
      ${renderInsights(item.insights)}
      <div class="details">${item.details.map((d, i) => renderRouteDetail(d, i)).join("<br>")}</div>
      ${renderScoreBreakdown(item.scoreBreakdown)}
      <button class="compare-btn" type="button">${state.selectedCompareIds.has(compareId) ? "移出对比" : "加入对比"}</button>
      <button class="route-btn" type="button">生成游览路线</button>
    </div>
  `;

  const icon = item.kind === "poi" ? poiIcon : gridIcon;
  const marker = L.marker([item.lat, item.lon], { icon })
    .addTo(map)
    .bindPopup(`<strong>${escapeHtml(item.name)}</strong><br>${item.avgMinutes} 分钟平均通勤`);
  state.recommendationMarkers.push(marker);

  card.addEventListener("click", () => {
    map.setView([item.lat, item.lon], 14);
    marker.openPopup();
  });
  card.querySelector(".route-btn").addEventListener("click", (event) => {
    event.stopPropagation();
    generateItinerary(item, card);
  });
  card.querySelector(".compare-btn").addEventListener("click", (event) => {
    event.stopPropagation();
    toggleCompare(compareId);
  });
  recommendationsEl.appendChild(card);
}

function renderScoreBreakdown(breakdown) {
  if (!breakdown) return "";
  const valueText = breakdown.value === null || breakdown.value === undefined ? "价格缺失" : breakdown.value;
  const preferenceText = breakdown.preferenceFit === null || breakdown.preferenceFit === undefined ? "未启用" : breakdown.preferenceFit;
  return `<div class="details">评分拆解：平均时间 ${breakdown.avgTime}，最长时间 ${breakdown.maxTime}，舒适性 ${breakdown.comfort}，性价比 ${valueText}，偏好匹配 ${preferenceText}。</div>`;
}

function toggleCompare(compareId) {
  if (state.selectedCompareIds.has(compareId)) {
    state.selectedCompareIds.delete(compareId);
  } else {
    if (state.selectedCompareIds.size >= 3) {
      shareOutput.textContent = "最多同时对比 3 家酒店。";
      return;
    }
    state.selectedCompareIds.add(compareId);
  }
  renderRecommendations(state.lastRecommendation);
}

function compareIdFor(item) {
  return item.id || `${item.name}-${item.lon}-${item.lat}`;
}

function bestClass(items, key, value, direction = "max") {
  const values = items.map((item) => Number(item[key])).filter((item) => Number.isFinite(item));
  if (!values.length || !Number.isFinite(Number(value))) return "";
  const best = direction === "min" ? Math.min(...values) : Math.max(...values);
  return Number(value) === best ? " best-cell" : "";
}

function renderComparison() {
  const items = ((state.lastRecommendation || {}).poiRecommendations || [])
    .filter((item) => state.selectedCompareIds.has(compareIdFor(item)));
  if (!items.length) {
    comparisonEl.classList.add("hidden");
    comparisonEl.innerHTML = "";
    return;
  }
  comparisonEl.classList.remove("hidden");
  const rows = [
    ["综合分", "score", "max", (item) => item.score],
    ["平均时间", "avgMinutes", "min", (item) => `${item.avgMinutes} 分`],
    ["最长时间", "maxMinutes", "min", (item) => `${item.maxMinutes} 分`],
    ["评分", "rating", "max", (item) => item.rating ? `${Number(item.rating).toFixed(1)}/5` : "缺失"],
    ["参考价", "price", "min", (item) => item.price ? `${Math.round(Number(item.price))}${item.priceUnit || "元"}` : "缺失"],
    ["性价比", "valueScore", "max", (item) => item.valueScore ?? "缺失"],
    ["偏好匹配", "preferenceFitScore", "max", (item) => item.preferenceFitScore ?? "未启用"],
    ["平均步行", "walkingAvgKilometers", "min", (item) => item.walkingAvgKilometers ? `${item.walkingAvgKilometers} km` : "缺失"],
    ["平均换乘", "transferAvgCount", "min", (item) => item.transferAvgCount !== null && item.transferAvgCount !== undefined ? `${item.transferAvgCount} 次` : "缺失"],
    ["数据来源", "marketDataSource", "max", (item) => item.marketDataSource || "估算"],
  ];
  comparisonEl.innerHTML = `
    <div class="comparison-heading">
      <strong>酒店对比</strong>
      <span>${items.length}/3</span>
    </div>
    <div class="comparison-table-wrap">
      <table class="comparison-table">
        <thead>
          <tr>
            <th>指标</th>
            ${items.map((item) => `<th>${escapeHtml(item.name)}</th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${rows.map(([label, key, direction, format]) => `
            <tr>
              <td>${label}</td>
              ${items.map((item) => `<td class="${bestClass(items, key, item[key], direction)}">${escapeHtml(format(item))}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderInsights(insights) {
  if (!insights) return "";
  const reasons = (insights.reasons || []).map((text) => `• ${escapeHtml(text)}`).join("<br>");
  const warnings = (insights.warnings || []).map((text) => `• ${escapeHtml(text)}`).join("<br>");
  return `
    <div class="insight-box">
      <strong>AI 推荐解读</strong>
      ${reasons || "暂无明显优势。"}
      ${insights.comparison ? `<div class="details">${escapeHtml(insights.comparison)}</div>` : ""}
      ${insights.weightsSummary ? `<div class="details">${escapeHtml(insights.weightsSummary)}</div>` : ""}
      ${warnings ? `<div class="warning-list"><strong>注意事项</strong>${warnings}</div>` : ""}
    </div>
  `;
}

function renderRouteDetail(detail, index) {
  const rows = [];
  if (detail.driving) rows.push(`驾车 ${detail.driving.minutes} 分 / ${detail.driving.kilometers} km`);
  if (detail.transit) {
    const extras = [
      detail.transit.walkingKilometers !== undefined ? `步行 ${detail.transit.walkingKilometers} km` : "",
      detail.transit.transfers !== undefined ? `换乘 ${detail.transit.transfers} 次` : "",
    ].filter(Boolean).join("，");
    rows.push(`公交 ${detail.transit.minutes} 分 / ${detail.transit.kilometers} km${extras ? `（${extras}）` : ""}`);
  }
  return `${escapeHtml(detail.destinationName || `目的地 ${index + 1}`)}：${rows.join("；")}`;
}

async function generateItinerary(hotel, card) {
  if (state.destinations.length === 0) return;
  clearRouteLayers();
  itineraryWorkspace.classList.remove("hidden");
  itineraryPanel.innerHTML = `<div class="empty">正在生成游览路线...</div>`;

  try {
    const routeMode = routeModeSelect.value === "transit" ? "transit" : "driving";
    const data = await api("/api/itinerary", {
      method: "POST",
      body: JSON.stringify({
        origin: { name: hotel.name, lon: hotel.lon, lat: hotel.lat },
        destinations: state.destinations,
        city: citySelect.value,
        routeMode,
        travelPreferences: getTravelPreferences(),
        startTime: startTimeInput.value || "09:00",
        stayMinutes: Number(stayMinutesInput.value || 60),
        returnToHotel: returnToHotelInput.checked,
      }),
    });
    state.currentItinerary = data;
    renderItinerary(data);
  } catch (error) {
    itineraryPanel.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

function renderItinerary(data) {
  itineraryWorkspace.classList.remove("hidden");
  const timelineRows = data.orderedStops
    .map((stop, index) => {
      const inboundSegment = data.segments[index];
      const inboundCard = inboundSegment ? renderSegmentCard(inboundSegment, index) : "";
      return `
      ${inboundCard}
      <div class="timeline-stop">
        <div class="timeline-icon">${index + 1}</div>
        <div>
          <div class="timeline-title">${escapeHtml(stop.name)}</div>
          <div class="timeline-meta">停留 ${stop.stayMinutes} 分钟</div>
        </div>
        <div class="time-pill">${escapeHtml(stop.arriveAt)} - ${escapeHtml(stop.leaveAt)}</div>
      </div>
    `;
    })
    .join("");
  const returnIndex = data.orderedStops.length;
  const returnSegment = data.segments[returnIndex];
  const returnCard = returnSegment ? renderSegmentCard(returnSegment, returnIndex) : "";
  itineraryPanel.innerHTML = `
    <div class="timeline-panel">
      <div class="timeline-stop">
        <div class="timeline-icon">出</div>
        <div>
          <div class="timeline-title">${escapeHtml(data.origin.name || "酒店")} - 出发</div>
          <div class="timeline-meta">按当前路线方式规划</div>
        </div>
        <div class="time-pill">${escapeHtml(data.startTime)}</div>
      </div>
      ${timelineRows}
      ${returnCard}
    </div>
    <div class="analysis-card">
      <div class="analysis-title">路线通行效率分析</div>
      <div class="details">总体能耗指数</div>
      <div class="efficiency-bar"><div class="efficiency-fill"></div></div>
      <div class="analysis-metrics">
        <div class="analysis-metric"><strong>${data.totalTravelMinutes} min</strong><span>今日总通勤时间</span></div>
        <div class="analysis-metric"><strong>${data.totalStayMinutes} min</strong><span>预计停留时间</span></div>
        <div class="analysis-metric"><strong>${data.totalKilometers} km</strong><span>交通距离</span></div>
      </div>
      <div class="analysis-tip">提示：当前路线根据高德返回的路线耗时生成，出发时间用于排程时间线，不代表实时车流预测。</div>
    </div>
  `;

  const routeGroup = [];
  data.segments.forEach((segment) => {
    const segmentIndex = state.routeSegmentLayers.length;
    const latlngs = (segment.polyline || []).map((point) => [point.lat, point.lon]);
    if (latlngs.length >= 2) {
      const color = routePalette[segmentIndex % routePalette.length];
      const line = L.polyline(latlngs, {
        color,
        weight: 5,
        opacity: 0.82,
      }).addTo(map);
      line.on("click", () => focusRouteSegment(segmentIndex));
      state.routeLayers.push(line);
      state.routeSegmentLayers.push(line);
      routeGroup.push(line);
    }
  });
  data.orderedStops.forEach((stop, index) => {
    const marker = L.marker([stop.lat, stop.lon], { icon: destinationIcon })
      .addTo(map)
      .bindPopup(`${index + 1}. ${escapeHtml(stop.name)}`);
    state.routeLayers.push(marker);
    routeGroup.push(marker);
  });
  if (routeGroup.length) {
    map.fitBounds(L.featureGroup(routeGroup).getBounds(), { padding: [54, 54] });
  }
  itineraryPanel.querySelectorAll(".segment-card").forEach((card) => {
    card.addEventListener("click", () => {
      focusRouteSegment(Number(card.dataset.segmentIndex));
    });
  });
}

function renderSegmentCard(segment, index) {
  return `
    <button class="segment-card" type="button" data-segment-index="${index}">
      <span class="segment-color" style="background:${routePalette[index % routePalette.length]}"></span>
      <span class="segment-main">
        <strong>${escapeHtml(segment.from.name)} → ${escapeHtml(segment.to.name)}</strong>
        <small>${escapeHtml(segment.departAt)}-${escapeHtml(segment.arriveAt)} · ${segment.minutes} 分 / ${segment.kilometers} km${segment.isReturn ? " · 返回酒店" : ""}</small>
      </span>
    </button>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

map.on("click", (event) => {
  addDestination({
    name: `地图点 ${state.destinations.length + 1}`,
    lon: event.latlng.lng,
    lat: event.latlng.lat,
  });
});

searchBtn.addEventListener("click", () => searchPois({ force: true }));
agentBtn.addEventListener("click", runAgent);
provinceSelect.addEventListener("change", () => {
  populateCitySelect();
  searchResults.innerHTML = "";
  if (searchInput.value.trim().length >= 2) schedulePoiSearch();
});
citySelect.addEventListener("change", () => {
  searchResults.innerHTML = "";
  if (searchInput.value.trim().length >= 2) schedulePoiSearch();
});
searchInput.addEventListener("input", schedulePoiSearch);
searchInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    clearTimeout(searchTimer);
    searchPois({ force: true });
  }
});
recommendBtn.addEventListener("click", recommend);
preferenceSelect.addEventListener("change", () => applyWeightPreset(preferenceSelect.value));
savePlanBtn.addEventListener("click", savePlan);
recommendPrevBtn.addEventListener("click", () => scrollRecommendationCards(-1));
recommendNextBtn.addEventListener("click", () => scrollRecommendationCards(1));
mapMiniBtn.addEventListener("click", toggleMiniMap);
mapCard.addEventListener("mousedown", startMiniMapDrag);
mapCard.addEventListener("touchstart", startMiniMapDrag, { passive: true });
feedbackOpenBtn.addEventListener("click", openFeedbackModal);
feedbackCloseBtn.addEventListener("click", closeFeedbackModal);
feedbackCancelBtn.addEventListener("click", closeFeedbackModal);
feedbackModal.addEventListener("click", (event) => {
  if (event.target === feedbackModal) closeFeedbackModal();
});
feedbackRating.querySelectorAll(".rating-btn").forEach((button) => {
  button.addEventListener("click", () => setFeedbackRating(Number(button.dataset.rating)));
});
feedbackSubmitBtn.addEventListener("click", submitFeedback);
window.addEventListener("beforeunload", (event) => {
  if (hasSubmittedFeedback() || !feedbackModal.classList.contains("hidden")) return;
  pendingExitFeedback = true;
  event.preventDefault();
  event.returnValue = "";
  setTimeout(() => {
    if (pendingExitFeedback && !hasSubmittedFeedback()) {
      openFeedbackModal();
    }
    pendingExitFeedback = false;
  }, 0);
});
[avgTimeWeight, maxTimeWeight, comfortWeight].forEach((input) => {
  input.addEventListener("input", syncWeightLabels);
});

populateProvinceSelect("湖北省");
populateCitySelect("武汉");
renderDestinations();
applyWeightPreset(preferenceSelect.value);
warmStatus().then(restorePlanFromUrl);
