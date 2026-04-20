export type DownloadSearch = {
    dataset?: string;
    year?: number;
    district?: string;
    school?: string;
    school_key?: number;
    gender?: string;
    race?: string;
    ethnicity?: string;
    sub_population?: string;
    grade?: string;
    limit: number;
    offset: number;
};

export type DistrictSearch = {
    year?: number;
    district?: string;
    school?: string;
};

export type RankingsSearch = {
    year?: number;
    limit: number;
    cursor?: string;
};
