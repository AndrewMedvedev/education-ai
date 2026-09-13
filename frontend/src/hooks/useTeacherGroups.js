import { useState } from "react";

const createDefaultTeacherGroups = () => [];

const clampProgress = (value) => Math.max(0, Math.min(100, value));

export function useTeacherGroups(courses, initialCourseId) {
  const fallbackCourseId = initialCourseId || courses[0]?.id || "";
  const [teacherGroups, setTeacherGroups] = useState(() =>
    createDefaultTeacherGroups(),
  );
  const [activeTeacherGroupId, setActiveTeacherGroupId] = useState("");
  const [teacherGroupName, setTeacherGroupName] = useState("Новый поток");
  const [teacherCourseId, setTeacherCourseId] = useState(fallbackCourseId);
  const [teacherStudentName, setTeacherStudentName] = useState("");

  const activeTeacherGroup =
    teacherGroups.find((group) => group.id === activeTeacherGroupId) ||
    teacherGroups[0] ||
    null;
  const activeTeacherCourse =
    courses.find(
      (course) =>
        course.id === (activeTeacherGroup?.courseId || teacherCourseId),
    ) || courses[0];
  const teacherLeaderboard = activeTeacherGroup
    ? [...activeTeacherGroup.students].sort(
        (a, b) =>
          b.progress - a.progress ||
          b.lessonsDone - a.lessonsDone ||
          a.name.localeCompare(b.name),
      )
    : [];

  const createTeacherGroup = () => {
    const nextName = teacherGroupName.trim();
    if (nextName.length < 2) {
      return;
    }

    const nextGroupId = `group-${Date.now()}`;
    setTeacherGroups((prev) => [
      ...prev,
      {
        id: nextGroupId,
        name: nextName,
        courseId: teacherCourseId,
        students: [],
      },
    ]);
    setActiveTeacherGroupId(nextGroupId);
    setTeacherGroupName("");
  };

  const addStudentToActiveGroup = () => {
    const nextName = teacherStudentName.trim();
    if (!activeTeacherGroup || nextName.length < 2) {
      return;
    }

    const nextStudent = {
      id: `student-${Date.now()}`,
      name: nextName,
      progress: 0,
      lessonsDone: 0,
    };

    setTeacherGroups((prev) =>
      prev.map((group) =>
        group.id === activeTeacherGroup.id
          ? { ...group, students: [...group.students, nextStudent] }
          : group,
      ),
    );
    setTeacherStudentName("");
  };

  const adjustStudentProgress = (studentId, delta) => {
    if (!activeTeacherGroup) {
      return;
    }

    setTeacherGroups((prev) =>
      prev.map((group) => {
        if (group.id !== activeTeacherGroup.id) {
          return group;
        }

        return {
          ...group,
          students: group.students.map((student) => {
            if (student.id !== studentId) {
              return student;
            }

            return {
              ...student,
              progress: clampProgress(student.progress + delta),
              lessonsDone: Math.max(
                0,
                student.lessonsDone + (delta > 0 ? 1 : delta < 0 ? -1 : 0),
              ),
            };
          }),
        };
      }),
    );
  };

  const simulateStudyTick = (studentId) => {
    const delta = Math.floor(Math.random() * 8) + 3;
    adjustStudentProgress(studentId, delta);
  };

  return {
    teacherGroups,
    activeTeacherGroup,
    setActiveTeacherGroupId,
    activeTeacherCourse,
    teacherGroupName,
    setTeacherGroupName,
    teacherCourseId,
    setTeacherCourseId,
    teacherStudentName,
    setTeacherStudentName,
    createTeacherGroup,
    addStudentToActiveGroup,
    adjustStudentProgress,
    simulateStudyTick,
    teacherLeaderboard,
  };
}
