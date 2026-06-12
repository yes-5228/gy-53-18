<script setup>
import { computed, onMounted, ref } from "vue";
import StatusBadge from "../components/StatusBadge.vue";
import StatGrid from "../components/StatGrid.vue";
import { parkingApi } from "../api/parking";

const spaces = ref([]);
const stats = ref({});
const zones = ref([]);
const floors = ref([]);
const loading = ref(false);
const error = ref("");
const selectedFloor = ref(null);
const selectedZone = ref(null);

const statItems = computed(() => [
  { label: "总车位", value: spaces.value.length },
  { label: "空闲", value: stats.value.free || 0 },
  { label: "占用", value: stats.value.occupied || 0 },
  { label: "预约", value: stats.value.reserved || 0 },
  { label: "维护", value: stats.value.maintenance || 0 },
]);

const filteredZones = computed(() => {
  if (selectedFloor.value === null) {
    return zones.value;
  }
  return zones.value.filter((z) => z.floor === selectedFloor.value);
});

async function loadSpaces() {
  loading.value = true;
  error.value = "";
  try {
    const params = {};
    if (selectedFloor.value !== null) {
      params.floor = selectedFloor.value;
    }
    if (selectedZone.value !== null) {
      params.zone_id = selectedZone.value;
    }
    const data = await parkingApi.getSpaces(params);
    spaces.value = data.items;
    stats.value = data.stats;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function loadZones() {
  try {
    const data = await parkingApi.getZones();
    zones.value = data.items;
  } catch (err) {
    console.error("加载区域失败", err);
  }
}

async function loadFloors() {
  try {
    const data = await parkingApi.getFloors();
    floors.value = data.items;
  } catch (err) {
    console.error("加载楼层失败", err);
  }
}

function handleFloorChange(floor) {
  selectedFloor.value = floor;
  selectedZone.value = null;
  loadSpaces();
}

function handleZoneChange(event) {
  const value = event.target.value;
  selectedZone.value = value ? parseInt(value) : null;
  loadSpaces();
}

async function updateStatus(space, status) {
  const plate = status === "occupied" ? space.plate_number || "临A00001" : null;
  await parkingApi.updateSpace(space.id, { status, plate_number: plate });
  await loadSpaces();
}

onMounted(() => {
  loadSpaces();
  loadZones();
  loadFloors();
});
</script>

<template>
  <div class="page-stack">
    <header class="page-header">
      <div>
        <h2>车位状态监控</h2>
        <p>实时查看车位占用、预约和维护状态。</p>
      </div>
      <button class="primary-button" type="button" @click="loadSpaces">刷新</button>
    </header>

    <div class="filter-bar">
      <div class="floor-tabs">
        <button
          :class="{ active: selectedFloor === null }"
          type="button"
          @click="handleFloorChange(null)"
        >
          全部楼层
        </button>
        <button
          v-for="floor in floors"
          :key="floor"
          :class="{ active: selectedFloor === floor }"
          type="button"
          @click="handleFloorChange(floor)"
        >
          {{ floor }}层
        </button>
      </div>
      <div class="zone-filter">
        <select :value="selectedZone || ''" @change="handleZoneChange">
          <option value="">全部区域</option>
          <option v-for="zone in filteredZones" :key="zone.id" :value="zone.id">
            {{ zone.name }} ({{ zone.code }})
          </option>
        </select>
      </div>
    </div>

    <StatGrid :stats="statItems" />
    <p v-if="error" class="error-text">{{ error }}</p>

    <div class="space-grid" :class="{ muted: loading }">
      <article v-for="space in spaces" :key="space.id" class="space-card">
        <div>
          <strong>{{ space.code }}</strong>
          <span>{{ space.zone_name || space.area }}</span>
        </div>
        <StatusBadge :status="space.status" />
        <p>{{ space.plate_number || "无绑定车辆" }}</p>
        <select :value="space.status" @change="updateStatus(space, $event.target.value)">
          <option value="free">空闲</option>
          <option value="occupied">占用</option>
          <option value="reserved">预约</option>
          <option value="maintenance">维护</option>
        </select>
      </article>
    </div>

    <div v-if="spaces.length === 0 && !loading" class="empty-state">
      <p>暂无车位数据</p>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.floor-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.floor-tabs button {
  background: #ffffff;
  border: 1px solid #cfdbd6;
  border-radius: 8px;
  color: #52645d;
  cursor: pointer;
  font-weight: 600;
  min-height: 36px;
  padding: 0 16px;
}

.floor-tabs button.active {
  background: #157f63;
  border-color: #157f63;
  color: #ffffff;
}

.zone-filter {
  min-width: 200px;
}

.zone-filter select {
  min-height: 36px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #65746e;
}

.muted {
  opacity: 0.6;
}
</style>

