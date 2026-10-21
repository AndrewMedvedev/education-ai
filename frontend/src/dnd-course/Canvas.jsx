import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  applyNodeChanges,
  Background,
  BackgroundVariant,
  MiniMap,
  Panel,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  useViewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useShallow } from "zustand/react/shallow";
import { COLUMN_GAP, DRAG_MIME, MODULE_LAYOUT, NODE_SIZE } from "./constants";
import { buildGraph, structureSignature } from "./graph";
import { parseNodeId } from "./helpers";
import { findFreeSlot, freeRects } from "./layout";
import Icon from "./icons";
import { nodeTypes } from "./nodes";
import { useDndCourseStore } from "./store";
import { useDndActions } from "./ui";

const TYPE_PRIORITY = { lesson: 4, material: 3, module: 2, course: 1 };

function classifyDrag(nodes) {
  const types = new Set(nodes.map((node) => node.type));
  if (types.size !== 1) return "mixed";
  const [type] = types;
  if (type === "material") return "materials";
  if (type === "lesson") return "lessons";
  if (type === "module") return nodes.length === 1 ? "module" : "mixed";
  return type;
}

function isEditableTarget(target) {
  return (
    target?.closest?.("input, textarea, select, [contenteditable='true'], .dnd-inspector, .dnd-modal") ||
    false
  );
}

function ZoomControls() {
  const { zoomIn, zoomOut, fitView, setViewport } = useReactFlow();
  const { zoom } = useViewport();
  const showUsed = useDndCourseStore((state) => state.showUsedMaterials);
  const usedCount = useDndCourseStore((state) => state.materials.filter((item) => item.lessonId).length);
  const toggleUsed = useDndCourseStore((state) => state.toggleUsedMaterials);
  return (
    <Panel position="top-right" className="dnd-zoom">
      <button type="button" className="dnd-icon-btn" onClick={() => zoomOut({ duration: 180 })} aria-label="Уменьшить масштаб" title="Уменьшить">
        <Icon name="zoomOut" />
      </button>
      <button
        type="button"
        className="dnd-zoom-value"
        onClick={() => setViewport({ x: 40, y: 40, zoom: 1 }, { duration: 200 })}
        title="Масштаб 100%"
        aria-label={`Текущий масштаб ${Math.round(zoom * 100)}%. Сбросить до 100%`}
      >
        {Math.round(zoom * 100)}%
      </button>
      <button type="button" className="dnd-icon-btn" onClick={() => zoomIn({ duration: 180 })} aria-label="Увеличить масштаб" title="Увеличить">
        <Icon name="zoomIn" />
      </button>
      <span className="dnd-zoom-sep" aria-hidden="true" />
      <button
        type="button"
        className={`dnd-icon-btn ${showUsed ? "is-on" : ""}`}
        onClick={toggleUsed}
        aria-pressed={showUsed}
        aria-label={showUsed ? "Скрыть материалы, которые уже в уроках" : `Показать материалы, которые уже в уроках (${usedCount})`}
        title={showUsed ? "Скрыть материалы, которые уже в уроках" : `Показать материалы, которые уже в уроках (${usedCount})`}
      >
        <Icon name="link" />
      </button>
      <button type="button" className="dnd-icon-btn" onClick={() => fitView({ padding: 0.2, duration: 260 })} aria-label="Вписать все элементы" title="Вписать все элементы">
        <Icon name="fit" />
      </button>
      <button
        type="button"
        className="dnd-icon-btn"
        onClick={() => fitView({ nodes: [{ id: "course" }], padding: 1.2, maxZoom: 1, duration: 260 })}
        aria-label="Вернуться к узлу курса"
        title="К узлу курса"
      >
        <Icon name="target" />
      </button>
    </Panel>
  );
}

function DropDock() {
  const dragKind = useDndCourseStore((state) => state.dragKind);
  const hint = useDndCourseStore((state) => state.dropHint);
  if (dragKind !== "materials" && dragKind !== "lessons") return null;
  const zone = dragKind === "materials" ? "new-lesson" : "new-module";
  const active = hint?.zone === zone;
  return (
    <div className="dnd-dock" aria-hidden="true">
      <div
        data-dnd-zone={zone}
        className={`dnd-dock-zone ${active ? (hint.valid ? "is-drop-ok" : "is-drop-bad") : ""}`}
      >
        <Icon name={zone === "new-lesson" ? "lesson" : "module"} size={20} />
        <span>
          <strong>{zone === "new-lesson" ? "Новый урок" : "Новый модуль"}</strong>
          <small>
            {zone === "new-lesson"
              ? "Отпустите материалы, чтобы собрать из них урок"
              : "Отпустите урок, чтобы создать модуль"}
          </small>
        </span>
      </div>
    </div>
  );
}

function DropReason() {
  const hint = useDndCourseStore((state) => state.dropHint);
  if (hint?.valid && hint.label) {
    return (
      <Panel position="bottom-center" className="dnd-drop-reason is-ok" role="status">
        <Icon name="module" size={16} />
        {hint.label}
      </Panel>
    );
  }
  if (!hint || hint.valid || !hint.reason) return null;
  return (
    <Panel position="bottom-center" className="dnd-drop-reason" role="status">
      <Icon name="alert" size={16} />
      {hint.reason}
    </Panel>
  );
}

function CanvasInner() {
  const rf = useReactFlow();
  const wrapperRef = useRef(null);
  const { pickFiles, requestDelete } = useDndActions();
  const signature = useDndCourseStore(structureSignature);
  const selectedIds = useDndCourseStore(useShallow((state) => state.selectedIds));
  const flash = useDndCourseStore((state) => state.flash);
  const activeNodeId = useDndCourseStore((state) => state.activeNodeId);
  const focusRequest = useDndCourseStore((state) => state.focusRequest);
  const initialViewport = useRef(useDndCourseStore.getState().viewport);
  const [syncTick, setSyncTick] = useState(0);
  const [fileOver, setFileOver] = useState(false);
  const [bouncing, setBouncing] = useState([]);
  const dragRef = useRef(null);
  const frameRef = useRef(0);

  const graph = useMemo(
    () => buildGraph(useDndCourseStore.getState()),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [signature, syncTick],
  );
  const [nodes, setNodes] = useState(graph.nodes);

  useEffect(() => {
    const selected = new Set(selectedIds);
    setNodes((previous) => {
      const byId = new Map(previous.map((node) => [node.id, node]));
      return graph.nodes.map((node) => {
        const prev = byId.get(node.id);
        return {
          ...node,
          position: prev?.dragging ? prev.position : node.position,
          dragging: prev?.dragging,
          measured: prev?.measured,
          selected: selected.has(node.id),
          className: bouncing.includes(node.id) ? "is-bouncing" : undefined,
        };
      });
    });
  }, [graph, selectedIds, bouncing]);

  const edges = useMemo(() => {
    const related = new Set([...selectedIds, activeNodeId].filter(Boolean));
    return graph.edges.map((edge) => ({
      ...edge,
      className: [
        "dnd-edge",
        `dnd-edge--${edge.kind}`,
        flash[edge.id] ? "is-new" : "",
        related.has(edge.source) || related.has(edge.target) ? "is-related" : "",
      ]
        .filter(Boolean)
        .join(" "),
      selectable: true,
      deletable: false,
      focusable: true,
      ariaLabel: edge.kind === "material" ? "Связь материал → урок" : "Связь модуль → курс",
    }));
  }, [graph.edges, flash, selectedIds, activeNodeId]);

  useEffect(() => {
    if (!focusRequest?.ids?.length) return undefined;
    const timer = window.setTimeout(() => {
      const known = focusRequest.ids.filter((id) => rf.getNode(id));
      if (known.length) {
        rf.fitView({ nodes: known.map((id) => ({ id })), padding: 0.25, maxZoom: 1, duration: 320 });
      }
    }, 80);
    return () => window.clearTimeout(timer);
  }, [focusRequest, rf]);

  const onNodesChange = useCallback((changes) => {
    setNodes((current) => applyNodeChanges(changes.filter((change) => change.type !== "remove"), current));
  }, []);

  const onSelectionChange = useCallback(({ nodes: picked }) => {
    useDndCourseStore.getState().setSelection(picked.map((node) => node.id));
  }, []);

  // ───── хит-тест по холсту ─────
  const hitTest = useCallback(
    (clientX, clientY, excludeIds = []) => {
      const zoneEl = document
        .elementsFromPoint(clientX, clientY)
        .find((element) => element.dataset?.dndZone);
      if (zoneEl) return { zone: zoneEl.dataset.dndZone };
      const point = rf.screenToFlowPosition({ x: clientX, y: clientY });
      const exclude = new Set(excludeIds);
      let best = null;
      rf.getNodes().forEach((node) => {
        if (exclude.has(node.id) || exclude.has(node.parentId) || node.type === "upload") return;
        const internal = rf.getInternalNode(node.id);
        const abs = internal?.internals?.positionAbsolute || node.position;
        const width = internal?.measured?.width || node.width || NODE_SIZE.material.width;
        const height = internal?.measured?.height || node.height || NODE_SIZE.material.height;
        if (point.x < abs.x || point.x > abs.x + width || point.y < abs.y || point.y > abs.y + height) return;
        if (!best || TYPE_PRIORITY[node.type] > TYPE_PRIORITY[best.node.type]) {
          best = { node, abs, width, height };
        }
      });
      return best ? { ...best, point } : { point };
    },
    [rf],
  );

  const evaluate = useCallback((kind, entityIds, hit) => {
    const state = useDndCourseStore.getState();
    const target = hit?.node;
    const targetType = target?.type;
    const targetEntity = target ? parseNodeId(target.id).entityId : null;

    if (kind === "materials") {
      if (hit?.zone === "new-lesson") {
        const check = state.validateMaterialsForLesson(entityIds);
        return { zone: "new-lesson", valid: check.ok, reason: check.reason, action: "new-lesson" };
      }
      if (targetType === "lesson") {
        const check = state.validateMaterialsForLesson(entityIds, targetEntity);
        return { targetId: target.id, valid: check.ok, reason: check.reason, action: "to-lesson", lessonId: targetEntity };
      }
      if (targetType === "module")
        return { targetId: target.id, valid: false, reason: "Материал нельзя добавить в модуль напрямую — сначала соберите из него урок." };
      if (targetType === "course")
        return { targetId: target.id, valid: false, reason: "Материал нельзя связать с курсом напрямую." };
      return { action: "move" };
    }

    if (kind === "lessons") {
      const nested = entityIds.some((id) => state.modules.some((module) => module.lessonIds.includes(id)));
      if (hit?.zone === "new-module") return { zone: "new-module", valid: true, action: "new-module" };
      let moduleId = null;
      let index = null;
      if (targetType === "module") {
        moduleId = targetEntity;
        const module = state.modules.find((item) => item.id === moduleId);
        index = hit.point.y < hit.abs.y + MODULE_LAYOUT.header ? 0 : module?.lessonIds.length ?? 0;
      } else if (targetType === "lesson" && target.parentId) {
        moduleId = parseNodeId(target.parentId).entityId;
        const module = state.modules.find((item) => item.id === moduleId);
        const base = module?.lessonIds.indexOf(targetEntity) ?? 0;
        index = hit.point.y > hit.abs.y + hit.height / 2 ? base + 1 : base;
      } else if (targetType === "lesson") {
        // Урок положили на свободный урок — предлагаем собрать из них новый модуль.
        return {
          targetId: target.id,
          valid: true,
          action: "merge-module",
          lessonIds: [targetEntity, ...entityIds.filter((id) => id !== targetEntity)],
          label:
            entityIds.length > 1
              ? "Отпустите, чтобы создать модуль из этих уроков"
              : "Отпустите, чтобы создать модуль из двух уроков",
        };
      } else if (targetType === "course") {
        return { targetId: target.id, valid: false, reason: "Сначала добавьте урок в модуль — модули связаны с курсом." };
      }
      if (moduleId) {
        return {
          targetId: targetType === "module" ? target.id : target.parentId,
          valid: true,
          action: "to-module",
          moduleId,
          index,
        };
      }
      if (nested) {
        return { valid: false, reason: "Урок нельзя вынести из модуля: перенесите его в другой модуль.", action: "revert" };
      }
      return { action: "move" };
    }

    if (kind === "module") {
      const module = state.modules.find((item) => item.id === entityIds[0]);
      if (!module) return { action: "revert" };
      if (targetType === "lesson" && !target.parentId)
        return { targetId: target.id, valid: false, reason: "Модуль нельзя добавить внутрь урока." };
      return { action: "reorder-module" };
    }

    return { action: "move" };
  }, []);

  const onNodeDragStart = useCallback((event, node, dragged) => {
    const list = dragged?.length ? dragged : [node];
    const kind = classifyDrag(list);
    dragRef.current = {
      kind,
      ids: list.map((item) => item.id),
      entityIds: list.map((item) => parseNodeId(item.id).entityId),
    };
    useDndCourseStore.getState().setDragKind(kind);
  }, []);

  const onNodeDrag = useCallback(
    (event) => {
      const drag = dragRef.current;
      if (!drag) return;
      const { clientX, clientY } = event;
      cancelAnimationFrame(frameRef.current);
      frameRef.current = requestAnimationFrame(() => {
        const result = evaluate(drag.kind, drag.entityIds, hitTest(clientX, clientY, drag.ids));
        const next =
          result.targetId || result.zone
            ? {
                targetId: result.targetId || null,
                zone: result.zone || null,
                valid: Boolean(result.valid),
                reason: result.reason || "",
                label: result.label || "",
              }
            : result.action === "revert"
              ? { targetId: null, zone: null, valid: false, reason: result.reason }
              : null;
        const current = useDndCourseStore.getState().dropHint;
        if (JSON.stringify(current) !== JSON.stringify(next)) {
          useDndCourseStore.getState().setDropHint(next);
        }
      });
    },
    [evaluate, hitTest],
  );

  const onNodeDragStop = useCallback(
    (event, node, dragged) => {
      cancelAnimationFrame(frameRef.current);
      const drag = dragRef.current;
      dragRef.current = null;
      const store = useDndCourseStore.getState();
      store.setDragKind(null);
      store.setDropHint(null);
      if (!drag) return;
      const list = dragged?.length ? dragged : [node];
      const result = evaluate(drag.kind, drag.entityIds, hitTest(event.clientX, event.clientY, drag.ids));
      const revert = () => setSyncTick((tick) => tick + 1);

      if (result.action === "move" || (drag.kind === "mixed" && !result.targetId)) {
        const patch = {};
        list.forEach((item) => {
          if (item.parentId || item.type === "module") return;
          patch[item.id] = { x: Math.round(item.position.x), y: Math.round(item.position.y) };
        });
        // На кнопку «Загрузить материалы» класть нельзя: карточка отскакивает в сторону.
        const upload = rf.getInternalNode("upload");
        const uploadAbs = upload?.internals?.positionAbsolute;
        const bounced = [];
        if (uploadAbs) {
          const uploadRect = { ...uploadAbs, ...NODE_SIZE.upload };
          const moved = Object.keys(patch);
          moved.forEach((id) => {
            const size = NODE_SIZE[parseNodeId(id).type] || NODE_SIZE.material;
            const point = patch[id];
            const overlap =
              point.x < uploadRect.x + uploadRect.width &&
              point.x + size.width > uploadRect.x &&
              point.y < uploadRect.y + uploadRect.height &&
              point.y + size.height > uploadRect.y;
            if (!overlap) return;
            const others = freeRects(store, moved).concat(
              moved.filter((other) => other !== id).map((other) => ({ ...patch[other], ...(NODE_SIZE[parseNodeId(other).type] || NODE_SIZE.material) })),
            );
            patch[id] = findFreeSlot(
              { x: point.x, y: uploadRect.y + uploadRect.height + COLUMN_GAP },
              size,
              others,
            );
            bounced.push(id);
          });
        }
        if (Object.keys(patch).length) store.setPositions(patch);
        if (bounced.length) {
          setBouncing(bounced);
          window.setTimeout(() => setBouncing([]), 450);
          store.announce("Карточка отодвинута: на кнопку загрузки класть нельзя.");
        }
        if (list.some((item) => item.parentId || item.type === "module")) revert();
        return;
      }

      // Модуль остаётся там, куда его перетащили (уроки внутри едут вместе с ним).
      // Остальные модули фиксируем на их текущих местах, чтобы они не перестраивались.
      if (drag.kind === "module" && result.action === "reorder-module") {
        const patch = {};
        rf.getNodes().forEach((item) => {
          if (item.type !== "module") return;
          const position = item.id === node.id ? node.position : item.position;
          patch[item.id] = { x: Math.round(position.x), y: Math.round(position.y) };
        });
        store.setPositions(patch);
      }
      revert();
      if (!result.valid && result.reason && result.action !== "reorder-module") {
        store.toast("warning", result.reason, { timeout: 3200 });
        return;
      }

      if (result.action === "new-lesson") {
        const ordered = store.selectedIds
          .filter((id) => drag.ids.includes(id))
          .map((id) => parseNodeId(id).entityId);
        const ids = ordered.length === drag.entityIds.length ? ordered : drag.entityIds;
        store.createLessonFromMaterials(ids);
      } else if (result.action === "to-lesson") {
        store.addMaterialsToLesson(result.lessonId, drag.entityIds);
      } else if (result.action === "new-module") {
        store.openModuleDialog(drag.entityIds);
      } else if (result.action === "merge-module") {
        store.openModuleDialog(result.lessonIds);
      } else if (result.action === "to-module") {
        (async () => {
          let index = result.index;
          for (const lessonId of drag.entityIds) {
            // eslint-disable-next-line no-await-in-loop
            await useDndCourseStore.getState().moveLessonToModule(lessonId, result.moduleId, index);
            if (index !== null) index += 1;
          }
        })();
      } else if (result.action === "reorder-module") {
        const ordered = [...store.modules].sort((a, b) => a.order - b.order);
        const centerY = node.position.y + (node.height || 200) / 2;
        let target = 0;
        ordered.forEach((module) => {
          if (module.id === drag.entityIds[0]) return;
          const internal = rf.getInternalNode(`module:${module.id}`);
          const abs = internal?.internals?.positionAbsolute;
          const height = internal?.measured?.height || 200;
          if (abs && centerY > abs.y + height / 2) target += 1;
        });
        store.reorderModule(drag.entityIds[0], target);
      }
    },
    [evaluate, hitTest, rf],
  );

  const isValidConnection = useCallback((connection) => {
    const source = parseNodeId(connection.source);
    const target = parseNodeId(connection.target);
    const state = useDndCourseStore.getState();
    if (source.type === "material" && target.type === "lesson") {
      return state.validateMaterialsForLesson([source.entityId], target.entityId).ok;
    }
    if (source.type === "lesson" && target.type === "module") {
      const module = state.modules.find((item) => item.id === target.entityId);
      return Boolean(module) && !module.lessonIds.includes(source.entityId);
    }
    // Линия от урока к уроку: свободный урок — новый модуль из двух уроков,
    // урок в модуле — переносим исходный урок в этот модуль.
    if (source.type === "lesson" && target.type === "lesson") {
      if (source.entityId === target.entityId) return false;
      const targetModule = state.modules.find((item) => item.lessonIds.includes(target.entityId));
      return !targetModule || !targetModule.lessonIds.includes(source.entityId);
    }
    return false;
  }, []);

  const onConnect = useCallback((connection) => {
    const source = parseNodeId(connection.source);
    const target = parseNodeId(connection.target);
    const store = useDndCourseStore.getState();
    if (source.type === "material" && target.type === "lesson") {
      store.addMaterialsToLesson(target.entityId, [source.entityId]);
    } else if (source.type === "lesson" && target.type === "module") {
      store.moveLessonToModule(source.entityId, target.entityId);
    } else if (source.type === "lesson" && target.type === "lesson") {
      const targetModule = store.modules.find((item) => item.lessonIds.includes(target.entityId));
      if (targetModule) {
        store.moveLessonToModule(
          source.entityId,
          targetModule.id,
          targetModule.lessonIds.indexOf(target.entityId) + 1,
        );
      } else {
        store.openModuleDialog([source.entityId, target.entityId]);
      }
    }
  }, []);

  const onNodeClick = useCallback((event, node) => {
    if (node.type === "upload") return;
    if (event.shiftKey || event.metaKey || event.ctrlKey) return;
    useDndCourseStore.getState().openInspector(node.id);
  }, []);

  // ───── файлы и элементы палитры ─────
  const onDragOver = useCallback((event) => {
    const types = [...(event.dataTransfer?.types || [])];
    if (!types.includes("Files") && !types.includes(DRAG_MIME)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    if (types.includes("Files")) setFileOver(true);
  }, []);

  const onDrop = useCallback(
    (event) => {
      const types = [...(event.dataTransfer?.types || [])];
      if (!types.includes("Files") && !types.includes(DRAG_MIME)) return;
      event.preventDefault();
      setFileOver(false);
      const store = useDndCourseStore.getState();
      const position = rf.screenToFlowPosition({ x: event.clientX, y: event.clientY });
      if (event.dataTransfer.files?.length) {
        const hit = hitTest(event.clientX, event.clientY);
        const lessonId = hit?.node?.type === "lesson" ? parseNodeId(hit.node.id).entityId : null;
        store.addFiles(event.dataTransfer.files, {
          position: lessonId ? null : { x: position.x - NODE_SIZE.material.width / 2, y: position.y - 30 },
          attachToLessonId: lessonId,
        });
        if (lessonId) store.toast("info", "Материал добавится в урок, как только документ будет обработан.");
        return;
      }
      const item = event.dataTransfer.getData(DRAG_MIME);
      if (item === "material") pickFiles({ position: { x: position.x - NODE_SIZE.material.width / 2, y: position.y - 30 } });
      if (item === "lesson") {
        const selectedMaterials = store.selectedIds
          .filter((id) => id.startsWith("material:"))
          .map((id) => parseNodeId(id).entityId);
        if (selectedMaterials.length) store.createLessonFromMaterials(selectedMaterials, { position });
        else store.openMaterialPicker();
      }
      if (item === "module") store.openModuleDialog([], { pick: true });
    },
    [hitTest, pickFiles, rf],
  );

  const onKeyDown = useCallback(
    (event) => {
      if (isEditableTarget(event.target)) return;
      const store = useDndCourseStore.getState();
      if (event.key === "Delete" || event.key === "Backspace") {
        const deletable = store.selectedIds.filter((id) => id !== "course");
        if (deletable.length === 1) {
          event.preventDefault();
          requestDelete(deletable[0]);
        } else if (deletable.length > 1) {
          event.preventDefault();
          store.toast("info", "Удаляйте элементы по одному — так случайно ничего не пропадёт.");
        }
      } else if (event.key === "Escape") {
        store.setSelection([]);
      }
    },
    [requestDelete],
  );

  return (
    <div
      ref={wrapperRef}
      className={`dnd-canvas ${fileOver ? "is-file-over" : ""}`}
      onDragOver={onDragOver}
      onDragLeave={(event) => {
        if (!wrapperRef.current?.contains(event.relatedTarget)) setFileOver(false);
      }}
      onDrop={onDrop}
      onKeyDown={onKeyDown}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onSelectionChange={onSelectionChange}
        onNodeDragStart={onNodeDragStart}
        onNodeDrag={onNodeDrag}
        onNodeDragStop={onNodeDragStop}
        onNodeClick={onNodeClick}
        onConnect={onConnect}
        isValidConnection={isValidConnection}
        onMoveEnd={(event, viewport) => useDndCourseStore.getState().setViewport(viewport)}
        defaultViewport={initialViewport.current}
        minZoom={0.25}
        maxZoom={2}
        panOnScroll
        zoomOnPinch
        zoomOnDoubleClick={false}
        selectionOnDrag={false}
        multiSelectionKeyCode={["Shift", "Meta", "Control"]}
        selectionKeyCode="Shift"
        deleteKeyCode={null}
        connectionRadius={36}
        nodeDragThreshold={4}
        elevateNodesOnSelect={false}
        proOptions={{ hideAttribution: true }}
        aria-label="Холст конструктора курса"
      >
        <Background id="dnd-bg-dots" variant={BackgroundVariant.Dots} gap={22} size={1.3} className="dnd-bg dnd-bg--dots" />
        <ZoomControls />
        <MiniMap
          className="dnd-minimap"
          pannable
          zoomable
          ariaLabel="Мини-карта холста"
          nodeClassName={(node) => `dnd-minimap-node is-${node.type}`}
          nodeBorderRadius={6}
        />
        <DropReason />
      </ReactFlow>
      <DropDock />
      {fileOver ? (
        <div className="dnd-file-over" aria-hidden="true">
          <Icon name="upload" size={28} />
          <strong>Отпустите файлы, чтобы добавить материалы</strong>
          <small>Положите файл на урок — материал добавится прямо в него</small>
        </div>
      ) : null}
    </div>
  );
}

export default function Canvas() {
  return (
    <ReactFlowProvider>
      <CanvasInner />
    </ReactFlowProvider>
  );
}
