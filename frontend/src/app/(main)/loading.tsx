export default function MainLoading() {
  return (
    <div className="flex h-full min-h-[50vh] flex-col items-center justify-center p-6 text-center">
      <div className="relative mb-4 h-10 w-10">
        <div className="absolute inset-0 rounded-full border-2 border-[var(--color-warm-gray-200)] opacity-40" />
        <div className="absolute inset-0 animate-spin rounded-full border-2 border-[var(--color-terracotta)] border-t-transparent" />
      </div>
      <p className="text-sm font-medium text-[var(--color-warm-gray-600)]">
        正在加载内容...
      </p>
      <p className="mt-1 text-xs text-[var(--color-warm-gray-400)]">
        EduAgent 正在为您准备学习资源
      </p>
    </div>
  );
}
