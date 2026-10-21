import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { safeLinkHref } from "./agentChatUtils";

const components = {
  a: ({ href, children }) => {
    const safeHref = safeLinkHref(href);
    if (!safeHref) return <span>{children}</span>;
    return (
      <a href={safeHref} target="_blank" rel="noopener noreferrer nofollow">
        {children}
      </a>
    );
  },
  img: () => null,
};

/** Markdown ответа агента без HTML и с безопасными ссылками. */
export default function AgentMarkdown({ children }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {String(children || "")}
    </ReactMarkdown>
  );
}
