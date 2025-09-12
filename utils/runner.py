import inspect


def run_intent_func(func, query=None, options=None, **extra_kwargs):
    """
    함수 시그니처를 검사해 안전하게 실행하는 공통 유틸
    - 인자 없음  → func()
    - 인자 1개   → func(query)
    - 인자 2개   → func(query, options)
    - *args/**kwargs 있으면 → query, options 전달 + extra_kwargs 병합
    """
    sig = inspect.signature(func)
    params = sig.parameters

    # 가변 인자 지원 여부 확인
    has_var_positional = any(
        p.kind == inspect.Parameter.VAR_POSITIONAL for p in params.values()
    )
    has_var_keyword = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )

    param_count = len(params)

    if param_count == 0:
        return func()
    elif param_count == 1 and not has_var_positional and not has_var_keyword:
        return func(query)
    elif param_count >= 2 and not (has_var_positional or has_var_keyword):
        return func(query, options)
    else:
        # *args / **kwargs 지원 함수라면 → 최대한 풍부하게 전달
        return func(query, options, **extra_kwargs)


