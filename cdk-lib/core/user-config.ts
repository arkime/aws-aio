/**
 * Structure to hold the user's input configuration
 */
export interface UserConfig {
    expectedTraffic: number;
    spiDays: number;
    historyDays: number;
    replicas: number;
    pcapDays: number;
}