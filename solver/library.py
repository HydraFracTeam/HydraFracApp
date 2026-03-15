def build_skin_library(df):
    """
    Построение библиотеки эталонных кривых из DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame с колонками Skin, h, N, W, L, a/L, X, Y
        
    Returns:
        Dict: Словарь {skin_value: [samples]}, где каждый sample содержит:
            - 'dynamic': DataFrame с колонками X, Y
            - 'h': эффективная толщина пласта
            - 'N': количество трещин
            - 'W': ширина трещины
            - 'L': полудлина трещины
            - 'a/L': отношение расстояния до границы к длине
    """

    full_grouped = df.groupby(['Skin', 'h', 'N', 'W', 'L', 'a/L'])

    skin_dict = {}

    for key, group in full_grouped:

        skin_value = key[0]

        sample = {}

        sample['dynamic'] = group[['X', 'Y']].reset_index(drop=True)

        sample['h'] = key[1]
        sample['N'] = key[2]
        sample['W'] = key[3]
        sample['L'] = key[4]
        sample['a/L'] = key[5]

        if skin_value not in skin_dict:
            skin_dict[skin_value] = []

        skin_dict[skin_value].append(sample)

    return skin_dict