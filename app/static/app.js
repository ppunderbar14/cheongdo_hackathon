(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const restaurantList = $("#restaurant-list");
  const awardList = $("#award-list");
  const locationStatus = $("#location-status");
  const searchInput = $("#search-input");
  const areaSelect = $("#area-select");
  const tasteResult = $("#taste-result");
  const reviewDialog = $("#review-dialog");
  const reviewForm = $("#review-form");
  let catalog = { restaurants: [], menus: [], reviews: [], awards: [] };
  let position = null;
  let requestId = 0;
  let debounceTimer = null;

  function node(tag, value, className = "") {
    const element = document.createElement(tag);
    element.textContent = value;
    element.className = className;
    return element;
  }

  function distanceLabel(meters) {
    if (!Number.isFinite(meters)) return "";
    return meters < 1000 ? `약 ${Math.round(meters)}m` : `약 ${(meters / 1000).toFixed(1)}km`;
  }

  function renderRestaurants(rows) {
    $("#result-count").textContent = rows.length ? `${rows.length}곳` : "";
    if (!rows.length) {
      restaurantList.replaceChildren(node(
        "p",
        "청도 식당 데이터가 아직 연결되지 않았어요. 검증된 식당·메뉴 자료를 등록한 뒤 주변 탐색과 월간 선정을 공개합니다.",
        "empty-state"
      ));
      return;
    }

    restaurantList.replaceChildren(...rows.map((restaurant) => {
      const card = document.createElement("article");
      card.className = "restaurant-card";
      card.append(node("div", "味", "restaurant-art"));
      const copy = document.createElement("div");
      copy.className = "restaurant-copy";
      copy.append(node("p", [restaurant.area, restaurant.distance_meters && distanceLabel(restaurant.distance_meters)].filter(Boolean).join(" · ")));
      copy.append(node("h3", restaurant.name));
      copy.append(node("p", restaurant.address || "주소 확인 필요"));
      copy.append(node("p", restaurant.source_checked_at ? `정보 확인 ${restaurant.source_checked_at}` : "정보 확인일 미등록", "restaurant-meta"));
      card.append(copy);

      const menus = catalog.menus.filter((menu) => menu.restaurant_id === restaurant.id);
      const menuList = document.createElement("div");
      menuList.className = "menu-list";
      if (!menus.length) menuList.append(node("p", "메뉴 평가를 준비 중이에요.", "section-note"));
      for (const menu of menus) {
        const row = document.createElement("div");
        row.className = "menu-row";
        const details = document.createElement("div");
        details.append(node("strong", menu.name));
        details.append(node("small", `${menu.review_count || 0}개 평가 · ${menu.unique_reviewers || 0}명`));
        const score = node("span", menu.unique_reviewers ? `★ ${Number(menu.rating).toFixed(1)}` : "평가 대기", "menu-score");
        const rateButton = node("button", "내 경험 기록", "rate-menu-button");
        rateButton.type = "button";
        rateButton.dataset.menuId = menu.id;
        const menuDetails = document.createElement("div");
        menuDetails.append(details, rateButton);
        row.append(menuDetails, score);
        menuList.append(row);
      }
      card.append(menuList);
      return card;
    }));
  }

  function renderAwards(awards) {
    awardList.replaceChildren();
    const safeAwards = Array.isArray(awards) ? awards : [];
    if (!safeAwards.length) {
      awardList.append(node("p", "공개 평가와 최소 표본 기준이 충족되면 Best 가게와 Best 메뉴를 발표합니다. 광고나 AI가 선정 점수에 영향을 주지 않아요.", "empty-state"));
      return;
    }
    for (const award of safeAwards) {
      const card = document.createElement("article");
      card.className = "award-card";
      card.append(node("strong", `${award.kind === "restaurant" ? "Best 가게" : "Best 메뉴"} · ${award.name}`));
      card.append(node("span", `${award.month} · ★ ${Number(award.rating).toFixed(1)} · ${award.unique_reviewers}명 평가`));
      awardList.append(card);
    }
  }

  async function loadCatalog() {
    const current = ++requestId;
    const params = new URLSearchParams();
    const query = searchInput.value.trim();
    const area = areaSelect.value;
    if (query) params.set("q", query);
    if (area) params.set("area", area);
    if (position) {
      params.set("lat", String(position.latitude));
      params.set("lon", String(position.longitude));
    }
    restaurantList.replaceChildren(node("p", "청도 맛집을 불러오는 중...", "empty-state"));
    try {
      const response = await fetch(`/api/catalog?${params}`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`catalog_http_${response.status}`);
      const result = await response.json();
      if (current !== requestId) return;
      catalog = result;
      renderRestaurants(result.restaurants || []);
      renderAwards(result.awards || []);
      $("#catalog-note").textContent = result.data_notice || "";
    } catch (error) {
      if (current !== requestId) return;
      console.error("맛집 목록 조회 실패", error);
      restaurantList.replaceChildren(node("p", "맛집 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.", "empty-state"));
    }
  }

  function requestLocation() {
    position = null;
    if (!navigator.geolocation || !window.isSecureContext) {
      locationStatus.textContent = "이 브라우저에서는 위치를 사용할 수 없어요. 지역 선택으로 찾아보세요.";
      void loadCatalog();
      return;
    }
    locationStatus.textContent = "현재 위치를 확인하고 있어요. 좌표는 저장하지 않습니다.";
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      position = { latitude: coords.latitude, longitude: coords.longitude };
      locationStatus.textContent = "주변 식당을 찾았어요. 현재 위치는 저장하지 않습니다.";
      void loadCatalog();
    }, (error) => {
      const reason = error.code === 1 ? "위치 권한이 거부됐어요." : error.code === 3 ? "위치 확인 시간이 초과됐어요." : "위치를 확인할 수 없어요.";
      locationStatus.textContent = `${reason} 지역 선택으로 찾아보세요.`;
      void loadCatalog();
    }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 });
  }

  function readLocalReviews() {
    try {
      const rows = JSON.parse(localStorage.getItem("cheongdo-taste-reviews") || "[]");
      return Array.isArray(rows) ? rows : [];
    } catch {
      return [];
    }
  }

  function openReview(menuId) {
    const menu = catalog.menus.find((item) => item.id === menuId);
    if (!menu) return;
    $("#review-menu-id").value = menu.id;
    $("#review-menu-name").textContent = menu.name;
    $("#review-score").value = "4.0";
    $("#review-score-output").value = "4.0";
    $("#review-tags").value = "";
    $("#review-message").textContent = "";
    reviewDialog.showModal();
  }

  reviewForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const menuId = $("#review-menu-id").value;
    const menu = catalog.menus.find((item) => item.id === menuId);
    if (!menu) {
      $("#review-message").textContent = "메뉴 정보를 다시 불러온 뒤 시도해 주세요.";
      return;
    }
    const tags = $("#review-tags").value.split(",").map((tag) => tag.trim()).filter(Boolean).slice(0, 8);
    const record = {
      menu_id: menuId,
      score: Number($("#review-score").value),
      tags,
      created_at: new Date().toISOString()
    };
    try {
      const reviews = readLocalReviews();
      reviews.push(record);
      localStorage.setItem("cheongdo-taste-reviews", JSON.stringify(reviews.slice(-100)));
      reviewDialog.close();
      tasteResult.textContent = "기록을 이 브라우저에 저장했어요. 취향 요약에서 확인할 수 있습니다.";
    } catch (error) {
      console.error("내 경험 기록 저장 실패", error);
      $("#review-message").textContent = "기록을 저장하지 못했어요. 브라우저 저장 공간을 확인해 주세요.";
    }
  });

  async function summarizeTaste() {
    const reviews = readLocalReviews();
    if (!reviews.length) {
      tasteResult.textContent = "아직 이 브라우저에 저장된 메뉴 평가가 없어요. 메뉴를 평가한 뒤 취향을 살펴볼 수 있어요.";
      return;
    }
    tasteResult.textContent = "내 기록에서 취향을 정리하고 있어요...";
    try {
      const response = await fetch("/api/taste-guide", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ reviews, menus: catalog.menus })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `taste_http_${response.status}`);
      tasteResult.textContent = result.summary;
    } catch (error) {
      console.error("취향 요약 실패", error);
      tasteResult.textContent = "AI 취향 요약을 사용할 수 없어요. 기록은 이 브라우저에 그대로 있어요.";
    }
  }

  $("#search-form").addEventListener("submit", (event) => {
    event.preventDefault();
    void loadCatalog();
  });
  searchInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => void loadCatalog(), 250);
  });
  areaSelect.addEventListener("change", () => {
    position = null;
    locationStatus.textContent = "선택한 청도 지역의 식당을 보여줍니다.";
    void loadCatalog();
  });
  $("#nearby-button").addEventListener("click", requestLocation);
  $("#taste-button").addEventListener("click", () => void summarizeTaste());
  $("#review-score").addEventListener("input", (event) => {
    $("#review-score-output").value = Number(event.currentTarget.value).toFixed(1);
  });
  $("#review-cancel").addEventListener("click", () => reviewDialog.close());
  restaurantList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-menu-id]");
    if (button) openReview(button.dataset.menuId);
  });

  void loadCatalog();
})();
