<script setup>
import { computed, onMounted, ref } from "vue";
import { parkingApi } from "../api/parking";

const zones = ref([]);
const floors = ref([]);
const loading = ref(false);
const error = ref("");
const showForm = ref(false);
const editingZone = ref(null);
const selectedFloor = ref(null);

const formData = ref({
  name: "",
  floor: 1,
  code: "",
  capacity: 0,
  maintenance_status: "normal",
  description: "",
});

const filteredZones = computed(() => {
  if (selectedFloor.value === null) {
    return zones.value;
  }
  return zones.value.filter((z) => z.floor === selectedFloor.value);
});

const maintenanceStatusOptions = [
  { value: "normal", label: "正常运营" },
  { value: "maintenance", label: "维护中" },
  { value: "closed", label: "已关闭" },
];

function getStatusLabel(status) {
  const option = maintenanceStatusOptions.find((o) => o.value === status);
  return option ? option.label : status;
}

function getStatusClass(status) {
  const classMap = {
    normal: "status-free",
    maintenance: "status-maintenance",
    closed: "status-expired",
  };
  return classMap[status] || "";
}

async function loadZones() {
  loading.value = true;
  error.value = "";
  try {
    const data = await parkingApi.getZones();
    zones.value = data.items;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
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

function openCreateForm() {
  editingZone.value = null;
  formData.value = {
    name: "",
    floor: 1,
    code: "",
    capacity: 0,
    maintenance_status: "normal",
    description: "",
  };
  showForm.value = true;
}

function openEditForm(zone) {
  editingZone.value = zone;
  formData.value = {
    name: zone.name,
    floor: zone.floor,
    code: zone.code,
    capacity: zone.capacity,
    maintenance_status: zone.maintenance_status,
    description: zone.description || "",
  };
  showForm.value = true;
}

function closeForm() {
  showForm.value = false;
  editingZone.value = null;
}

async function handleSubmit() {
  try {
    if (editingZone.value) {
      try {
        await parkingApi.updateZone(editingZone.value.id, formData.value);
      } catch (err) {
        if (err.need_confirm) {
          if (!confirm(err.message)) {
            return;
          }
          await parkingApi.updateZone(editingZone.value.id, { ...formData.value, force: true });
        } else {
          throw err;
        }
      }
    } else {
      await parkingApi.createZone(formData.value);
    }
    await loadZones();
    await loadFloors();
    closeForm();
  } catch (err) {
    error.value = err.message || "操作失败";
  }
}

async function handleDelete(zone) {
  if (!confirm(`确定要删除区域「${zone.name}」吗？`)) {
    return;
  }
  try {
    await parkingApi.deleteZone(zone.id);
    await loadZones();
    await loadFloors();
  } catch (err) {
    error.value = err.message || "删除失败";
  }
}

async function toggleMaintenance(zone) {
  const nextStatus = zone.maintenance_status === "normal" ? "maintenance" : "normal";
  try {
    await parkingApi.updateZone(zone.id, { maintenance_status: nextStatus });
    await loadZones();
  } catch (err) {
    if (err.need_confirm) {
      if (confirm(err.message)) {
        try {
          await parkingApi.updateZone(zone.id, { maintenance_status: nextStatus, force: true });
          await loadZones();
        } catch (err2) {
          error.value = err2.message || "操作失败";
        }
      }
    } else {
      error.value = err.message || "操作失败";
    }
  }
}

onMounted(() => {
  loadZones();
  loadFloors();
});
</script>

<template>
  <div class="page-stack">
    <header class="page-header">
      <div>
        <h2>区域管理</h2>
        <p>管理停车场的楼层和分区，维护区域容量和运营状态。</p>
      </div>
      <button class="primary-button" type="button" @click="openCreateForm">新增区域</button>
    </header>

    <div class="filter-bar">
      <div class="floor-tabs">
        <button
          :class="{ active: selectedFloor === null }"
          type="button"
          @click="selectedFloor = null"
        >
          全部楼层
        </button>
        <button
          v-for="floor in floors"
          :key="floor"
          :class="{ active: selectedFloor === floor }"
          type="button"
          @click="selectedFloor = floor"
        >
          {{ floor }}层
        </button>
      </div>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>

    <div class="zone-grid" :class="{ muted: loading }">
      <article v-for="zone in filteredZones" :key="zone.id" class="zone-card">
        <div class="zone-header">
          <div>
            <h3>{{ zone.name }}</h3>
            <span class="zone-code">{{ zone.code }} · {{ zone.floor }}层</span>
          </div>
          <span :class="['status-badge', getStatusClass(zone.maintenance_status)]">
            {{ getStatusLabel(zone.maintenance_status) }}
          </span>
        </div>

        <div class="zone-stats">
          <div class="stat-item">
            <span class="stat-label">容量</span>
            <strong class="stat-value">{{ zone.capacity }}</strong>
          </div>
          <div class="stat-item">
            <span class="stat-label">已占用</span>
            <strong class="stat-value occupied">{{ zone.occupied_count }}</strong>
          </div>
          <div class="stat-item">
            <span class="stat-label">维护中</span>
            <strong class="stat-value maintenance">{{ zone.maintenance_count }}</strong>
          </div>
          <div class="stat-item">
            <span class="stat-label">预约</span>
            <strong class="stat-value reserved">{{ zone.reserved_count }}</strong>
          </div>
          <div class="stat-item">
            <span class="stat-label">空闲</span>
            <strong :class="['stat-value', zone.free_count === 0 ? 'zero' : 'free']">{{ zone.free_count }}</strong>
          </div>
        </div>

        <p v-if="zone.description" class="zone-desc">{{ zone.description }}</p>

        <div class="zone-actions">
          <button class="small-button" type="button" @click="toggleMaintenance(zone)">
            {{ zone.maintenance_status === "normal" ? "设为维护" : "恢复运营" }}
          </button>
          <button class="secondary-button" type="button" @click="openEditForm(zone)">编辑</button>
          <button class="secondary-button danger" type="button" @click="handleDelete(zone)">删除</button>
        </div>
      </article>
    </div>

    <div v-if="filteredZones.length === 0 && !loading" class="empty-state">
      <p>暂无区域数据，点击「新增区域」开始创建。</p>
    </div>

    <div v-if="showForm" class="modal-overlay" @click.self="closeForm">
      <div class="modal-content">
        <header class="modal-header">
          <h3>{{ editingZone ? "编辑区域" : "新增区域" }}</h3>
          <button type="button" class="close-btn" @click="closeForm">×</button>
        </header>

        <form class="modal-body" @submit.prevent="handleSubmit">
          <div class="form-grid">
            <label>
              区域名称
              <input v-model="formData.name" type="text" placeholder="如：A区" required />
            </label>

            <label>
              区域编码
              <input v-model="formData.code" type="text" placeholder="如：F1-A" required />
            </label>

            <label>
              楼层
              <input v-model.number="formData.floor" type="number" min="1" required />
            </label>

            <label>
              容量（车位数量）
              <input v-model.number="formData.capacity" type="number" min="0" />
            </label>

            <label>
              运营状态
              <select v-model="formData.maintenance_status">
                <option v-for="opt in maintenanceStatusOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </label>
          </div>

          <label>
            描述说明
            <textarea v-model="formData.description" rows="3" placeholder="可选，补充区域说明"></textarea>
          </label>

          <footer class="modal-footer">
            <button type="button" class="secondary-button" @click="closeForm">取消</button>
            <button type="submit" class="primary-button">
              {{ editingZone ? "保存修改" : "创建区域" }}
            </button>
          </footer>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.zone-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
}

.zone-card {
  background: #ffffff;
  border: 1px solid #dde6e1;
  border-radius: 10px;
  box-shadow: 0 10px 28px rgb(30 50 42 / 8%);
  display: grid;
  gap: 14px;
  padding: 18px;
}

.zone-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.zone-header h3 {
  font-size: 18px;
  margin: 0 0 4px;
}

.zone-code {
  color: #65746e;
  font-size: 13px;
}

.zone-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  padding: 12px;
  background: #f6faf8;
  border-radius: 8px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  color: #6b7c75;
  font-size: 12px;
  display: block;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
}

.stat-value.free {
  color: #146346;
}

.stat-value.occupied {
  color: #9b2e1c;
}

.stat-value.reserved {
  color: #805600;
}

.stat-value.maintenance {
  color: #4c5964;
}

.stat-value.zero {
  color: #ffffff;
  background: #c0392b;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 18px;
}

.zone-desc {
  color: #65746e;
  font-size: 13px;
  margin: 0;
}

.zone-actions {
  display: flex;
  gap: 8px;
}

.zone-actions .secondary-button {
  flex: 1;
  min-height: 34px;
  font-size: 13px;
}

.zone-actions .danger {
  color: #9b2e1c;
  background: #fde4df;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #65746e;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #ffffff;
  border-radius: 12px;
  max-width: 560px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px;
  border-bottom: 1px solid #e5ece8;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: #65746e;
  line-height: 1;
  padding: 0 8px;
}

.modal-body {
  padding: 22px;
  display: grid;
  gap: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

textarea {
  background: #fbfdfc;
  border: 1px solid #cfdbd6;
  border-radius: 8px;
  color: #16211d;
  padding: 10px;
  width: 100%;
  font: inherit;
  resize: vertical;
  min-height: 80px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.muted {
  opacity: 0.6;
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .zone-stats {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
