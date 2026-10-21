import { useParams } from "react-router-dom";
import CoursePreview from "../dnd-course/CoursePreview";
import "../styles/dnd-course.css";

export default function DragAndDropCoursePreviewPage() {
  const { courseId } = useParams();
  return <CoursePreview key={courseId} courseId={courseId} />;
}
