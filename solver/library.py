def build_skin_library(df):

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
