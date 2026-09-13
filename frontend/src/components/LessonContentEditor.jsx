import { Fragment, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  createAgentConversationKey,
  useAgentStore,
} from "../stores/agentStore";
import { useSessionStore } from "../stores/sessionStore";
import { convertDocumentToMarkdown } from "../utils/api";
import { attachmentsApi } from "../utils/attachments";
import { getMediaId, getMediaUrl, MEDIA_FOLDERS } from "../utils/media";
import {
  allowedImageExtension,
  allowedImageTypes,
  allowedTextExtension,
  blockToMarkdown,
  blockTypes,
  createBlock,
  detectType,
  getBlockTitle,
  joinBlocks,
  MAX_CONTENT_BLOCKS,
  markdownComponents,
  normalizeContentBlocks,
  safeMarkdownUrl,
  stripUiFields,
  templates,
} from "../lesson/lessonEditorConfig";

const IMAGE_MAX_SIZE_BYTES = 15 * 1024 * 1024;
const MAX_AI_REFERENCE_IMAGES = 2;

function getUserId(user) {
  return user?.id || user?.user_id || user?.userId || "";
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = "";

  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }

  return btoa(binary);
}

async function readFileAsBase64(file) {
  return arrayBufferToBase64(await file.arrayBuffer());
}

async function readImageUrlAsBase64(url) {
  if (!url) return null;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(
      "Не удалось прочитать текущее изображение блока для AI-редактора.",
    );
  }
  return arrayBufferToBase64(await response.arrayBuffer());
}

function getUploadedImageId(uploadResult) {
  return getMediaId(
    uploadResult?.storage_key ||
      uploadResult?.storageKey ||
      uploadResult?.file_id ||
      uploadResult?.fileId ||
      uploadResult?.image_id ||
      uploadResult?.imageId ||
      uploadResult?.id ||
      uploadResult?.attachment_id,
  );
}

export default function LessonContentEditor({
  courseId,
  lesson,
  onChange,
  contentLabel = "Теория",
  blocksLabel = "",
  showInsertControls = true,
}) {
  const [blocks, setBlocks] = useState(() =>
    normalizeContentBlocks(
      lesson.contentBlocks || lesson.content_blocks,
      lesson.markdown || lesson.content || "",
    ),
  );
  const [activeBlockId, setActiveBlockId] = useState("");
  const [insertIndex, setInsertIndex] = useState(null);
  const [isAiOpen, setIsAiOpen] = useState(false);
  const [aiInput, setAiInput] = useState("");
  const [aiReferenceImages, setAiReferenceImages] = useState([]);
  const [aiReferenceError, setAiReferenceError] = useState("");
  const [proposal, setProposal] = useState(null);
  const [proposalError, setProposalError] = useState("");
  const [blockLimitError, setBlockLimitError] = useState("");
  const aiConversationKey = createAgentConversationKey(
    "editor",
    courseId,
    `${lesson.id}:${activeBlockId}`,
  );
  const aiConversation = useAgentStore(
    (state) => state.conversations[aiConversationKey],
  );
  const sendAgentMessage = useAgentStore((state) => state.sendMessage);
  const cancelAgentRequest = useAgentStore((state) => state.cancelRequest);
  const user = useSessionStore((state) => state.user);
  const loadCurrentUser = useSessionStore((state) => state.loadCurrentUser);
  const currentUserId = getUserId(user);
  const isAiSending = aiConversation?.status === "loading";
  const aiError =
    proposalError || aiReferenceError || aiConversation?.error || "";
  const [uploadingImageBlockId, setUploadingImageBlockId] = useState("");
  const [imageUploadError, setImageUploadError] = useState("");
  const [imageUploadPreview, setImageUploadPreview] = useState(null);
  const fileInputRef = useRef(null);
  const aiImageInputRef = useRef(null);
  const aiMessagesRef = useRef(null);
  const blockRefs = useRef(new Map());
  const aiReferenceImagesRef = useRef([]);
  const imageUploadPreviewRef = useRef(null);

  useEffect(() => {
    const nextBlocks = normalizeContentBlocks(
      lesson.contentBlocks || lesson.content_blocks,
      lesson.markdown || lesson.content || "",
    );
    setBlocks(nextBlocks);
    setActiveBlockId("");
    setInsertIndex(null);
    setIsAiOpen(false);
    setAiInput("");
    setAiReferenceImages((current) => {
      current.forEach((image) => URL.revokeObjectURL(image.previewUrl));
      return [];
    });
    setAiReferenceError("");
    setImageUploadPreview((current) => {
      if (current?.previewUrl) URL.revokeObjectURL(current.previewUrl);
      return null;
    });
    setImageUploadError("");
    setUploadingImageBlockId("");
    setProposal(null);
    setProposalError("");
    setBlockLimitError("");
  }, [lesson.id]);

  useEffect(
    () => () => cancelAgentRequest(aiConversationKey),
    [aiConversationKey, cancelAgentRequest],
  );

  useEffect(() => {
    aiReferenceImagesRef.current = aiReferenceImages;
  }, [aiReferenceImages]);

  useEffect(() => {
    imageUploadPreviewRef.current = imageUploadPreview;
  }, [imageUploadPreview]);

  useEffect(
    () => () => {
      aiReferenceImagesRef.current.forEach((image) =>
        URL.revokeObjectURL(image.previewUrl),
      );
      const preview = imageUploadPreviewRef.current;
      if (preview?.previewUrl) URL.revokeObjectURL(preview.previewUrl);
    },
    [],
  );

  useEffect(() => {
    if (!activeBlockId) {
      return;
    }
    window.requestAnimationFrame(() => {
      blockRefs.current.get(activeBlockId)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "nearest",
      });
    });
  }, [activeBlockId]);

  useEffect(() => {
    if (!user) {
      loadCurrentUser();
    }
  }, [loadCurrentUser, user]);

  useEffect(() => {
    const container = aiMessagesRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [aiConversation?.messages, isAiSending]);

  const commitBlocks = (nextBlocks, nextActiveId = activeBlockId) => {
    const normalizedBlocks =
      nextBlocks.length > 0
        ? nextBlocks
        : [createBlock(templates.text, "text")];
    setBlocks(normalizedBlocks);
    setActiveBlockId(
      nextActiveId &&
        normalizedBlocks.some((block) => block.id === nextActiveId)
        ? nextActiveId
        : "",
    );
    onChange({
      contentBlocks: normalizedBlocks.map(stripUiFields),
      markdown: joinBlocks(normalizedBlocks),
      content: "",
    });
  };

  const updateBlock = (blockId, changes) => {
    commitBlocks(
      blocks.map((block) =>
        block.id === blockId ? { ...block, ...changes } : block,
      ),
      blockId,
    );
  };

  const updateQuestion = (blockId, questionIndex, changes) => {
    const target = blocks.find((block) => block.id === blockId);
    if (!target) return;

    const questions = [...(target.questions || [])];
    questions[questionIndex] = { ...questions[questionIndex], ...changes };
    updateBlock(blockId, { questions });
  };

  const addQuestion = (blockId) => {
    const target = blocks.find((block) => block.id === blockId);
    if (!target) return;
    updateBlock(blockId, {
      questions: [...(target.questions || []), { question: "", answer: "" }],
    });
  };

  const removeQuestion = (blockId, questionIndex) => {
    const target = blocks.find((block) => block.id === blockId);
    if (!target) return;
    const questions = (target.questions || []).filter(
      (_, index) => index !== questionIndex,
    );
    updateBlock(blockId, {
      questions: questions.length ? questions : [{ question: "", answer: "" }],
    });
  };

  const insertBlockAt = (index, type) => {
    if (blocks.length >= MAX_CONTENT_BLOCKS) {
      setBlockLimitError(
        `В уроке может быть не более ${MAX_CONTENT_BLOCKS} блоков.`,
      );
      setInsertIndex(null);
      return;
    }

    setBlockLimitError("");
    const safeIndex = Math.min(Math.max(index, 0), blocks.length);
    const newBlock = createBlock(templates[type], type);
    const nextBlocks = [
      ...blocks.slice(0, safeIndex),
      newBlock,
      ...blocks.slice(safeIndex),
    ];
    commitBlocks(nextBlocks, newBlock.id);
    setInsertIndex(null);
    setIsAiOpen(false);
    setProposal(null);
  };

  const deleteBlock = (blockId) => {
    const targetIndex = blocks.findIndex((block) => block.id === blockId);
    const nextBlocks = blocks.filter((block) => block.id !== blockId);
    const nextActive = nextBlocks[Math.max(0, targetIndex - 1)]?.id;
    commitBlocks(nextBlocks, nextActive);
    setIsAiOpen(false);
    setProposal(null);
  };

  const moveBlock = (blockId, direction) => {
    const currentIndex = blocks.findIndex((block) => block.id === blockId);
    const nextIndex = currentIndex + direction;
    if (currentIndex < 0 || nextIndex < 0 || nextIndex >= blocks.length) {
      return;
    }

    const nextBlocks = [...blocks];
    [nextBlocks[currentIndex], nextBlocks[nextIndex]] = [
      nextBlocks[nextIndex],
      nextBlocks[currentIndex],
    ];
    commitBlocks(nextBlocks, blockId);
  };

  const uploadCourseImageFile = async (file) => {
    if (!currentUserId) {
      throw new Error(
        "Не удалось определить пользователя для загрузки изображения.",
      );
    }

    const uploadResult = await attachmentsApi.uploadAttachment(
      file,
      MEDIA_FOLDERS.COURSE_IMAGES,
      currentUserId,
      {
        folder: MEDIA_FOLDERS.COURSE_IMAGES,
        maxSizeBytes: IMAGE_MAX_SIZE_BYTES,
        allowedMimeTypes: allowedImageTypes,
      },
    );
    const imageId = getUploadedImageId(uploadResult);
    if (!imageId) {
      throw new Error("Хранилище не вернуло идентификатор изображения.");
    }
    return imageId;
  };

  const importFiles = async (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) {
      return;
    }

    const availableSlots = Math.max(0, MAX_CONTENT_BLOCKS - blocks.length);
    if (availableSlots === 0) {
      setBlockLimitError(
        `В уроке может быть не более ${MAX_CONTENT_BLOCKS} блоков.`,
      );
      event.target.value = "";
      return;
    }

    setBlockLimitError(
      files.length > availableSlots
        ? `Будут добавлены только первые ${availableSlots} файлов: лимит — ${MAX_CONTENT_BLOCKS} блоков.`
        : "",
    );
    const importedContent = [];
    for (const file of files) {
      if (importedContent.length >= availableSlots) {
        break;
      }
      if (
        allowedImageTypes.has(file.type) ||
        (file.type === "" && allowedImageExtension.test(file.name))
      ) {
        try {
          const imageId = await uploadCourseImageFile(file);
          importedContent.push({ type: "image", data: { image_id: imageId } });
        } catch (error) {
          setBlockLimitError(
            error?.message || "Не удалось загрузить изображение в хранилище.",
          );
        }
        continue;
      }

      if (!allowedTextExtension.test(file.name)) {
        continue;
      }

      let text = "";
      if (/\.(pdf|docx|pptx|xlsx|html)$/i.test(file.name)) {
        const converted = await convertDocumentToMarkdown(file);
        text =
          typeof converted === "string" ? converted : converted?.markdown || "";
      } else {
        text = await file.text();
      }
      text = text.trim();
      if (text) {
        importedContent.push({ type: detectType(text), data: text });
      }
    }

    if (importedContent.length > 0) {
      const activeIndex = blocks.findIndex(
        (block) => block.id === activeBlockId,
      );
      const insertAt = activeIndex >= 0 ? activeIndex + 1 : blocks.length;
      const importedBlocks = importedContent.map((item) =>
        createBlock(item.data, item.type),
      );
      commitBlocks(
        [
          ...blocks.slice(0, insertAt),
          ...importedBlocks,
          ...blocks.slice(insertAt),
        ],
        importedBlocks[0]?.id,
      );
    }
    event.target.value = "";
  };

  const askAi = async () => {
    const prompt = aiInput.trim();
    const activeBlock = blocks.find((block) => block.id === activeBlockId);
    const isImageBlock = activeBlock?.content_type === "image";
    if (!prompt || isAiSending) {
      return;
    }
    if (!activeBlock || activeBlock.content_type === "video") {
      return;
    }

    const currentBlock = stripUiFields(activeBlock);
    setProposalError("");
    setAiReferenceError("");
    setAiInput("");

    try {
      const currentImageBase64 = isImageBlock
        ? await readImageUrlAsBase64(
            getMediaUrl(
              currentUserId,
              MEDIA_FOLDERS.COURSE_IMAGES,
              activeBlock.image_id,
            ),
          )
        : null;
      const referenceImageBase64 = isImageBlock
        ? await Promise.all(
            aiReferenceImages.map((image) => readFileAsBase64(image.file)),
          )
        : [];
      const images = [currentImageBase64, ...referenceImageBase64].filter(
        Boolean,
      );
      const response = await sendAgentMessage({
        key: aiConversationKey,
        agent: "editor",
        courseId,
        content: prompt,
        contentBlocks: blocks
          .filter((block) => block.id !== activeBlock.id)
          .map(stripUiFields),
        editorPayload: {
          content_type: activeBlock.content_type,
          content_block: JSON.stringify(currentBlock),
          images: isImageBlock && images.length > 0 ? images : undefined,
        },
        emptyResponseMessage: "",
        responseDisplayMessage: (agentResponse) =>
          agentResponse?.parsedContent &&
          typeof agentResponse.parsedContent === "object" &&
          !Array.isArray(agentResponse.parsedContent)
            ? isImageBlock
              ? "Изображение обновлено. Результат уже сохранён в хранилище."
              : "Правка готова. Проверьте предложенный вариант и примените его, если он подходит."
            : "",
      });
      if (!response) return;
      if (
        !response.parsedContent ||
        typeof response.parsedContent !== "object" ||
        Array.isArray(response.parsedContent)
      ) {
        setProposalError(
          "ИИ вернул ответ в неподдерживаемом формате. Попробуйте уточнить запрос.",
        );
        return;
      }

      const proposedBlock = {
        ...response.parsedContent,
        content_type: activeBlock.content_type,
        ai_generated: true,
      };
      if (isImageBlock) {
        const imageId = getMediaId(
          response.parsedContent.image_id || response.parsedContent.imageId,
        );
        if (!imageId) {
          setProposalError("ИИ не вернул идентификатор готового изображения.");
          return;
        }
        updateBlock(activeBlock.id, { image_id: imageId, ai_generated: true });
        setAiReferenceImages((current) => {
          current.forEach((image) => URL.revokeObjectURL(image.previewUrl));
          return [];
        });
        return;
      }
      setProposal({
        blockId: activeBlock.id,
        block: proposedBlock,
        content: blockToMarkdown(proposedBlock),
      });
    } catch (error) {
      if (!error?.status) {
        setProposalError(error?.message || "Не удалось отправить запрос ИИ.");
      }
      // Публичная сетевая ошибка API хранится в Zustand-store.
    }
  };

  const addAiReferenceFiles = (files) => {
    const selectedFiles = Array.from(files || []);
    if (selectedFiles.length === 0) return;

    const nextImages = [];
    const errors = [];
    let slotsLeft = MAX_AI_REFERENCE_IMAGES - aiReferenceImages.length;

    selectedFiles.forEach((file) => {
      if (slotsLeft <= 0) {
        errors.push(
          `Можно приложить не более ${MAX_AI_REFERENCE_IMAGES} референсов.`,
        );
        return;
      }
      if (!allowedImageTypes.has(file.type)) {
        errors.push(
          `${file.name || "Файл"}: выберите изображение PNG, JPEG, WebP или GIF.`,
        );
        return;
      }
      if (file.size > IMAGE_MAX_SIZE_BYTES) {
        errors.push(`${file.name}: файл больше 15 МБ.`);
        return;
      }
      nextImages.push({
        id: `ai-ref-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        file,
        name: file.name,
        previewUrl: URL.createObjectURL(file),
      });
      slotsLeft -= 1;
    });

    setAiReferenceError([...new Set(errors)].join(" "));
    if (nextImages.length > 0) {
      setAiReferenceImages((current) => [...current, ...nextImages]);
    }
  };

  const attachAiImages = (event) => {
    addAiReferenceFiles(event.target.files);
    event.target.value = "";
  };

  const removeAiReferenceImage = (imageId) => {
    setAiReferenceImages((current) =>
      current.filter((image) => {
        if (image.id === imageId) {
          URL.revokeObjectURL(image.previewUrl);
          return false;
        }
        return true;
      }),
    );
    setAiReferenceError("");
  };

  const applyProposal = () => {
    if (!proposal) {
      return;
    }
    const target = blocks.find((block) => block.id === proposal.blockId);
    if (!target) return;

    updateBlock(proposal.blockId, proposal.block);
    setProposal(null);
    setIsAiOpen(false);
  };

  const rejectProposal = () => {
    setProposal(null);
  };

  const scrollToBlock = (blockId) => {
    window.requestAnimationFrame(() => {
      blockRefs.current.get(blockId)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "nearest",
      });
    });
  };

  const selectBlock = (blockId) => {
    setActiveBlockId(blockId);
    setInsertIndex(null);
    setIsAiOpen(false);
    setAiInput("");
    setAiReferenceImages((current) => {
      current.forEach((image) => URL.revokeObjectURL(image.previewUrl));
      return [];
    });
    setAiReferenceError("");
    setProposal(null);
    scrollToBlock(blockId);
  };

  const renderTextAreaField = (block, field, label, placeholder, rows = 5) => (
    <label className="lesson-block-field lesson-block-field-wide">
      <span>{label}</span>
      <textarea
        value={block[field] || ""}
        onChange={(event) =>
          updateBlock(block.id, { [field]: event.target.value })
        }
        placeholder={placeholder}
        rows={rows}
      />
    </label>
  );

  const renderInputField = (block, field, label, placeholder) => (
    <label className="lesson-block-field">
      <span>{label}</span>
      <input
        value={block[field] || ""}
        onChange={(event) =>
          updateBlock(block.id, { [field]: event.target.value })
        }
        placeholder={placeholder}
      />
    </label>
  );

  const uploadImageBlockFile = async (block, file) => {
    if (!file) return;
    setImageUploadError("");

    if (block.image_id) {
      setImageUploadError(
        "В image-блоке может быть только одно изображение. Удалите текущее перед новой загрузкой.",
      );
      return;
    }

    if (!allowedImageTypes.has(file.type)) {
      setImageUploadError("Выберите изображение PNG, JPEG, WebP или GIF.");
      return;
    }
    if (file.size > IMAGE_MAX_SIZE_BYTES) {
      setImageUploadError("Максимальный размер изображения — 15 МБ.");
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    setImageUploadPreview((current) => {
      if (current?.previewUrl) URL.revokeObjectURL(current.previewUrl);
      return { blockId: block.id, previewUrl, name: file.name };
    });
    setUploadingImageBlockId(block.id);

    try {
      const imageId = await uploadCourseImageFile(file);
      updateBlock(block.id, { image_id: imageId, ai_generated: false });
      setImageUploadPreview((current) => {
        if (current?.previewUrl) URL.revokeObjectURL(current.previewUrl);
        return null;
      });
    } catch (error) {
      setImageUploadError(
        error?.message || "Не удалось загрузить изображение в хранилище.",
      );
    } finally {
      setUploadingImageBlockId("");
    }
  };

  const renderImageBlockFields = (block) => {
    const currentImageUrl = getMediaUrl(
      currentUserId,
      MEDIA_FOLDERS.COURSE_IMAGES,
      block.image_id,
    );
    const activePreview =
      imageUploadPreview?.blockId === block.id ? imageUploadPreview : null;
    const previewUrl = activePreview?.previewUrl || currentImageUrl;
    const isUploading = uploadingImageBlockId === block.id;
    const canUploadImage = !isUploading && !block.image_id;

    return (
      <div className="lesson-block-field lesson-block-field-wide lesson-image-block-editor">
        <span>Итоговое изображение блока</span>
        <label
          className={`lesson-image-block-dropzone ${previewUrl ? "has-image" : ""} ${!canUploadImage ? "is-disabled" : ""}`}
          onDragOver={(event) => {
            if (canUploadImage) event.preventDefault();
          }}
          onDrop={(event) => {
            event.preventDefault();
            if (!canUploadImage) {
              setImageUploadError(
                "В image-блоке уже есть изображение. Удалите его перед новой загрузкой.",
              );
              return;
            }
            const [file] = Array.from(event.dataTransfer.files || []);
            uploadImageBlockFile(block, file);
          }}
        >
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            disabled={!canUploadImage}
            onChange={(event) => {
              const [file] = Array.from(event.target.files || []);
              event.target.value = "";
              if (!canUploadImage) {
                setImageUploadError(
                  "В image-блоке уже есть изображение. Удалите его перед новой загрузкой.",
                );
                return;
              }
              uploadImageBlockFile(block, file);
            }}
          />
          {previewUrl ? (
            <div className="lesson-image-block-preview">
              <img src={previewUrl} alt="Предпросмотр изображения блока" />
              {activePreview && <small>{activePreview.name}</small>}
            </div>
          ) : (
            <div className="lesson-image-block-empty">
              <strong>
                {isUploading ? "Загружаем..." : "Перетащите изображение сюда"}
              </strong>
              <small>
                или нажмите, чтобы выбрать файл. PNG, JPEG, WebP или GIF до 15
                МБ.
              </small>
            </div>
          )}
        </label>
        <div className="lesson-image-block-actions">
          <small>
            В блоке хранится одно изображение. Чтобы загрузить другое, сначала
            удалите текущее.
          </small>
          {block.image_id && (
            <button
              type="button"
              className="btn btn-outline"
              disabled={isUploading}
              onClick={() => {
                setImageUploadError("");
                updateBlock(block.id, { image_id: "", ai_generated: false });
              }}
            >
              Удалить изображение
            </button>
          )}
        </div>
        {imageUploadError && (
          <p className="lesson-ai-error">{imageUploadError}</p>
        )}
      </div>
    );
  };

  const renderBlockFields = (block) => {
    switch (block.content_type) {
      case "text":
        return renderTextAreaField(
          block,
          "md_content",
          "Текст лекции",
          "Введите Markdown-контент",
          12,
        );
      case "video":
        return (
          <>
            {renderInputField(block, "url", "Ссылка на видео", "https://...")}
            {renderTextAreaField(
              block,
              "description",
              "Описание",
              "Кратко опишите видео",
              4,
            )}
          </>
        );
      case "image":
        return renderImageBlockFields(block);
      case "program_code":
        return (
          <>
            {renderInputField(block, "language", "Язык", "python")}
            {renderTextAreaField(
              block,
              "code",
              "Код",
              "Введите пример кода",
              10,
            )}
            {renderTextAreaField(
              block,
              "explanation",
              "Пояснение",
              "Что делает этот код",
              4,
            )}
          </>
        );
      case "mermaid":
        return (
          <>
            {renderInputField(
              block,
              "title",
              "Заголовок",
              "Название диаграммы",
            )}
            {renderTextAreaField(
              block,
              "md_content",
              "Код Mermaid",
              "flowchart TD\n  A --> B",
              9,
            )}
            {renderTextAreaField(
              block,
              "explanation",
              "Описание",
              "Поясните диаграмму",
              4,
            )}
          </>
        );

      case "quiz":
        return (
          <div className="lesson-block-field lesson-block-field-wide lesson-quiz-editor">
            <span>Вопросы</span>
            {(block.questions || []).map((question, questionIndex) => (
              <div
                className="lesson-quiz-question"
                key={`question-${questionIndex}`}
              >
                <label>
                  <span>Вопрос {questionIndex + 1}</span>
                  <input
                    value={question.question || ""}
                    onChange={(event) =>
                      updateQuestion(block.id, questionIndex, {
                        question: event.target.value,
                      })
                    }
                    placeholder="Введите вопрос"
                  />
                </label>
                <label>
                  <span>Ответ</span>
                  <textarea
                    value={question.answer || ""}
                    onChange={(event) =>
                      updateQuestion(block.id, questionIndex, {
                        answer: event.target.value,
                      })
                    }
                    placeholder="Введите правильный ответ"
                  />
                </label>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => removeQuestion(block.id, questionIndex)}
                >
                  Удалить вопрос
                </button>
              </div>
            ))}
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => addQuestion(block.id)}
            >
              Добавить вопрос
            </button>
          </div>
        );
      case "math_formula":
      case "chemical_formula":
      case "musical_notation":
        return (
          <>
            {renderTextAreaField(
              block,
              "formula",
              "Формула / запись",
              "Введите формулу или нотацию",
              4,
            )}
            {renderTextAreaField(
              block,
              "explanation",
              "Пояснение",
              "Поясните значение",
              4,
            )}
          </>
        );
      default:
        return null;
    }
  };

  const renderInsertControl = (index) => (
    <div
      className={`lesson-insert-control ${insertIndex === index ? "is-open" : ""}`}
    >
      <button
        type="button"
        className={`lesson-insert-line ${insertIndex === index ? "is-active" : ""}`}
        onClick={() =>
          setInsertIndex((current) => (current === index ? null : index))
        }
      >
        {insertIndex === index ? "Скрыть" : "Вставить здесь"}
      </button>
      {insertIndex === index && (
        <div className="lesson-editor-palette lesson-insert-palette">
          {blockTypes.map((type) => (
            <button
              key={type.id}
              type="button"
              onClick={() => insertBlockAt(index, type.id)}
            >
              <strong>{type.label}</strong>
              <span>{type.hint}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );

  const renderAiEditor = (block) => (
    <aside className="lesson-ai-editor">
      <div className="lesson-ai-editor-head">
        <span>ИИ-редактор</span>
        <button
          type="button"
          onClick={() => setIsAiOpen(false)}
          aria-label="Свернуть ИИ-редактор"
          title="Свернуть ИИ-редактор"
        >
          −
        </button>
      </div>
      <div
        className="lesson-ai-messages"
        ref={aiMessagesRef}
        aria-live="polite"
        aria-busy={isAiSending}
      >
        {(aiConversation?.messages || []).length === 0 && (
          <div className="lesson-ai-message is-assistant">
            <p>
              Опишите, что нужно изменить. Я подготовлю правку, а история
              диалога останется здесь.
            </p>
          </div>
        )}
        {(aiConversation?.messages || []).map((message) => (
          <div
            key={message.id}
            className={`lesson-ai-message is-${message.role}`}
          >
            <p>{message.text}</p>
            {message.role === "user" && (
              <span className="chat-message-status">✓ Отправлено</span>
            )}
          </div>
        ))}
        {isAiSending && (
          <div className="lesson-ai-message is-assistant is-thinking">
            <span className="chat-thinking-dots" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <span>ИИ получил сообщение и готовит правку…</span>
          </div>
        )}
      </div>
      {block.content_type === "image" && aiReferenceImages.length > 0 && (
        <div className="lesson-ai-reference-grid">
          {aiReferenceImages.map((image) => (
            <div className="lesson-ai-reference-preview" key={image.id}>
              <img src={image.previewUrl} alt={image.name} />
              <button
                type="button"
                onClick={() => removeAiReferenceImage(image.id)}
                aria-label={`Удалить ${image.name}`}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
      {aiError && <p className="lesson-ai-error">{aiError}</p>}
      <div
        className={`lesson-ai-composer ${block.content_type === "image" ? "has-attach" : ""}`}
      >
        {block.content_type === "image" && (
          <>
            <input
              ref={aiImageInputRef}
              className="lesson-ai-image-input"
              type="file"
              accept="image/*"
              multiple
              onChange={attachAiImages}
            />
            <button
              type="button"
              className="lesson-ai-attach"
              onClick={() => aiImageInputRef.current?.click()}
              aria-label="Прикрепить референсы до 15 МБ"
              title="Прикрепить референсы до 15 МБ"
            >
              +
            </button>
          </>
        )}
        <textarea
          value={aiInput}
          onChange={(event) => setAiInput(event.target.value)}
          placeholder={
            isAiSending
              ? "Можно написать следующее сообщение — отправка после ответа"
              : "Напишите, что нужно изменить"
          }
          maxLength={10_000}
          onKeyDown={(event) => {
            if (event.nativeEvent.isComposing) return;
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              askAi();
            }
          }}
        />
        <button
          type="button"
          className="lesson-ai-send"
          onClick={askAi}
          disabled={isAiSending || !aiInput.trim()}
          aria-label="Отправить сообщение"
          title="Отправить"
        >
          ↑
        </button>
      </div>
    </aside>
  );

  return (
    <div className="lesson-content-editor">
      <div className="lesson-content-editor-head">
        <div>
          <span>{contentLabel}</span>
          <strong>{blocksLabel}</strong>
        </div>
        <input
          ref={fileInputRef}
          className="knowledge-file-input"
          type="file"
          multiple
          accept=".pdf,.docx,.pptx,.xlsx,.md,.markdown,.html,.txt,.json,.sql,.js,.jsx,.ts,.tsx,.py,.csv,.png,.jpg,.jpeg,.webp,.gif"
          onChange={importFiles}
        />
      </div>

      {blockLimitError && (
        <p className="lesson-editor-limit-error">{blockLimitError}</p>
      )}

      <div className="lesson-content-editor-layout">
        <div className="lesson-editor-blocks">
          {showInsertControls &&
            blocks.length < MAX_CONTENT_BLOCKS &&
            renderInsertControl(0)}
          {blocks.map((block, index) => {
            const isActive = activeBlockId === block.id;
            const canUseAiEditor = block.content_type !== "video";
            return (
              <Fragment key={block.id}>
                <div
                  ref={(element) => {
                    if (element) {
                      blockRefs.current.set(block.id, element);
                    } else {
                      blockRefs.current.delete(block.id);
                    }
                  }}
                  className={`lesson-editor-block-row ${isActive && isAiOpen && canUseAiEditor ? "has-ai" : ""}`}
                >
                  <article
                    className={`lesson-editor-block is-${block.type} ${isActive ? "is-active" : "is-preview"}`}
                  >
                    {proposal && proposal.blockId === block.id ? (
                      <div className="lesson-block-proposal">
                        <div className="lesson-block-proposal-head">
                          <span>Предложено ИИ</span>
                          <div className="lesson-block-proposal-actions">
                            <button
                              type="button"
                              className="btn btn-solid"
                              onClick={applyProposal}
                            >
                              Применить
                            </button>
                            <button
                              type="button"
                              className="btn btn-outline"
                              onClick={rejectProposal}
                            >
                              Не применять
                            </button>
                          </div>
                        </div>
                        <div className="lesson-markdown lesson-proposal-preview">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={markdownComponents}
                            urlTransform={safeMarkdownUrl}
                          >
                            {proposal.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    ) : isActive ? (
                      <>
                        <div className="lesson-editor-block-head">
                          <strong>{getBlockTitle(block)}</strong>
                          <div>
                            <button
                              type="button"
                              onClick={() => moveBlock(block.id, -1)}
                              disabled={index === 0}
                            >
                              Выше
                            </button>
                            <button
                              type="button"
                              onClick={() => moveBlock(block.id, 1)}
                              disabled={index === blocks.length - 1}
                            >
                              Ниже
                            </button>
                            {canUseAiEditor && (
                              <button
                                type="button"
                                className={isAiOpen ? "is-active" : ""}
                                onClick={() => {
                                  setIsAiOpen((current) => !current);
                                  scrollToBlock(block.id);
                                }}
                              >
                                ИИ-редактор
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => setActiveBlockId("")}
                            >
                              Готово
                            </button>
                            <button
                              type="button"
                              onClick={() => deleteBlock(block.id)}
                            >
                              Удалить
                            </button>
                          </div>
                        </div>
                        <div className="lesson-block-fields">
                          {renderBlockFields(block)}
                        </div>
                      </>
                    ) : (
                      <div
                        className="lesson-editor-block-select"
                        onClick={() => selectBlock(block.id)}
                        role="button"
                        tabIndex={0}
                        aria-label={`Редактировать блок ${index + 1}: ${getBlockTitle(block)}`}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            selectBlock(block.id);
                          }
                        }}
                      >
                        <div className="lesson-editor-preview-head">
                          <span>
                            {blockTypes.find((type) => type.id === block.type)
                              ?.label || "Блок"}
                          </span>
                          <strong>{getBlockTitle(block)}</strong>
                        </div>
                        <div className="lesson-markdown">
                          {block.content_type === "image" ? (
                            block.image_id ? (
                              <img
                                className="lesson-image-block-preview-img"
                                src={getMediaUrl(
                                  currentUserId,
                                  MEDIA_FOLDERS.COURSE_IMAGES,
                                  block.image_id,
                                )}
                                alt="Изображение блока"
                              />
                            ) : (
                              "Блок пока пуст."
                            )
                          ) : (
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={markdownComponents}
                              urlTransform={safeMarkdownUrl}
                            >
                              {blockToMarkdown(block) || "Блок пока пуст."}
                            </ReactMarkdown>
                          )}
                        </div>
                      </div>
                    )}
                  </article>
                  {isActive &&
                    isAiOpen &&
                    canUseAiEditor &&
                    renderAiEditor(block)}
                </div>
                {showInsertControls &&
                  blocks.length < MAX_CONTENT_BLOCKS &&
                  renderInsertControl(index + 1)}
              </Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
