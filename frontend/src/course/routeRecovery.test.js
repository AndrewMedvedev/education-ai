import assert from "node:assert/strict";
import { test } from "node:test";
import {
  EMPTY_COURSE, EMPTY_BLOCK, EMPTY_LESSON,
  getSelectedCourse, getSelectedBlock, getSelectedLesson, getSelectedPractice,
  mergeCourse, mergeCoursePage, mergeModule,
} from "./courseState.js";
import { getRouteState } from "../utils/routeState.js";

function fixture() {
  return [{
    id: "course", title: "Course", blocks: [
      { id: "first", lessons: [{ id: "first-lesson" }], practice: [{ id: "first-practice" }] },
      { id: "target", lessons: [{ id: "lesson", title: "Loaded", content: "theory" }], practice: [{ id: "practice" }] },
    ],
  }];
}

const modes = ["", "/edit", "/metrics"];
const contents = [["lesson", "lesson"], ["lessons", "lesson"], ["practice", "practice"], ["block", "target"]];

for (const mode of modes) {
  test(`empty cache preserves course URL identity in ${mode || "view"} mode`, () => {
    assert.deepEqual(getRouteState(`/course/course${mode}`, []), {
      courseId: "course", blockId: null, lessonId: null, practiceId: null,
    });
    assert.equal(getSelectedCourse([], "course"), EMPTY_COURSE);
  });
  for (const [type, id] of contents) {
    const path = `/course/course${mode}/${type}/${id}`;
    test(`empty cache preserves explicit ${path}`, () => {
      const state = getRouteState(path, []);
      assert.equal(state.courseId, "course");
      assert.equal(state.blockId, type === "block" ? id : null);
      assert.equal(state.lessonId, type === "lesson" || type === "lessons" ? id : null);
      assert.equal(state.practiceId, type === "practice" ? id : null);
    });
    test(`loaded cache resolves ${path} to its owning module`, () => {
      const courses = fixture();
      const state = getRouteState(path, courses);
      assert.deepEqual(state, { courseId: "course", blockId: "target", lessonId: "lesson", practiceId: "practice" });
      const course = getSelectedCourse(courses, state.courseId);
      const block = getSelectedBlock(course, state.blockId);
      assert.equal(block.id, "target");
      assert.equal(getSelectedLesson(block, state.lessonId).id, "lesson");
      assert.equal(getSelectedPractice(block, state.practiceId).id, "practice");
    });
    test(`unknown explicit ${type} in ${mode || "view"} never selects first cached entity`, () => {
      const courses = fixture();
      const state = getRouteState(`/course/course${mode}/${type}/unknown`, courses);
      const course = getSelectedCourse(courses, state.courseId);
      const block = getSelectedBlock(course, state.blockId);
      if (type === "block") {
        assert.equal(state.blockId, "unknown");
        assert.equal(block, EMPTY_BLOCK);
        assert.equal(state.lessonId, null);
      } else if (type === "practice") {
        assert.equal(state.practiceId, "unknown");
        assert.equal(getSelectedPractice(block, state.practiceId), null);
      } else {
        assert.equal(state.lessonId, "unknown");
        assert.equal(getSelectedLesson(block, state.lessonId), EMPTY_LESSON);
      }
    });
  }
  test(`unknown explicit course in ${mode || "view"} never selects first course`, () => {
    const courses = fixture();
    const state = getRouteState(`/course/unknown${mode}/lesson/unknown-lesson`, courses);
    assert.equal(state.courseId, "unknown");
    assert.equal(state.lessonId, "unknown-lesson");
    assert.equal(state.blockId, null);
    assert.equal(getSelectedCourse(courses, state.courseId), EMPTY_COURSE);
  });
}

test("only absent selection IDs allow first-item fallback", () => {
  const courses = fixture();
  const course = courses[0];
  const block = course.blocks[0];
  assert.equal(getSelectedCourse(courses, null), course);
  assert.equal(getSelectedBlock(course, null), block);
  assert.equal(getSelectedLesson(block, null), block.lessons[0]);
  assert.equal(getSelectedPractice(block, null), block.practice[0]);
  assert.equal(getSelectedCourse(courses, "unknown"), EMPTY_COURSE);
  assert.equal(getSelectedBlock(course, "unknown"), EMPTY_BLOCK);
  assert.equal(getSelectedLesson(block, "unknown"), EMPTY_LESSON);
  assert.equal(getSelectedPractice(block, "unknown"), null);
});

test("empty full module response removes old lessons and practice without mutating cache", () => {
  const courses = fixture();
  const before = structuredClone(courses);
  const updated = mergeModule(courses[0], { id: "target", lessons: [], practice: [] });
  assert.deepEqual(updated.blocks[1].lessons, []);
  assert.deepEqual(updated.blocks[1].practice, []);
  assert.equal(updated.blocks[0], courses[0].blocks[0]);
  assert.deepEqual(courses, before);
  const route = getRouteState("/course/course/edit/lesson/lesson", [updated]);
  assert.equal(route.lessonId, "lesson");
  assert.equal(route.blockId, null);
  assert.equal(getSelectedLesson(updated.blocks[1], route.lessonId), EMPTY_LESSON);
});

test("partial module response without lesson fields preserves loaded data", () => {
  const course = fixture()[0];
  const updated = mergeModule(course, { id: "target", title: "Updated" });
  assert.equal(updated.blocks[1].lessons, course.blocks[1].lessons);
  assert.equal(updated.blocks[1].practice, course.blocks[1].practice);
});

for (const merge of [mergeCourse, (courses, next) => mergeCoursePage(courses, [next])]) {
  test(`${merge === mergeCourse ? "detail" : "page"} course refs do not overwrite loaded module lessons`, () => {
    const courses = fixture();
    const original = structuredClone(courses);
    const refs = { id: "course", title: "Updated", blocks: [
      { id: "target", title: "Ref title", lessons: [], practice: [] },
      { id: "new" },
    ] };
    const updated = merge(courses, refs)[0];
    assert.equal(updated.title, "Updated");
    assert.equal(updated.blocks[0].title, "Ref title");
    assert.equal(updated.blocks[0].lessons, courses[0].blocks[1].lessons);
    assert.equal(updated.blocks[0].practice, courses[0].blocks[1].practice);
    assert.deepEqual(updated.blocks.map((block) => block.id), ["target", "new"]);
    assert.deepEqual(courses, original);
  });
}

test("late course refs preserve an authoritative empty module result", () => {
  const loaded = mergeModule(fixture()[0], { id: "target", lessons: [], practice: [] });
  const updated = mergeCourse([loaded], {
    id: "course", blocks: [{ id: "target", lessons: [{ id: "old" }], practice: [{ id: "old-practice" }] }],
  })[0];
  assert.deepEqual(updated.blocks[0].lessons, []);
  assert.deepEqual(updated.blocks[0].practice, []);
});

test("empty cache recovers URL selection as course refs and module details arrive", () => {
  const path = "/course/course/metrics/lessons/lesson";
  let courses = [];
  assert.equal(getRouteState(path, courses).lessonId, "lesson");
  courses = mergeCourse(courses, { id: "course", blocks: [{ id: "target" }] });
  assert.equal(getRouteState(path, courses).blockId, null);
  courses = courses.map((course) => mergeModule(course, { id: "target", lessons: [{ id: "lesson" }], practice: [] }));
  assert.equal(getRouteState(path, courses).blockId, "target");
  courses = mergeCourse(courses, { id: "course", blocks: [{ id: "target", lessons: [] }] });
  assert.equal(getRouteState(path, courses).blockId, "target");
});
