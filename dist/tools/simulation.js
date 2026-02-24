/**
 * Simulation tools (mrgsolve)
 * Author: Husain Z Attarwala, PhD
 */
export const simulateRegimenTool = {
    name: 'simulate_regimen',
    description: 'Simulate a dosing regimen using mrgsolve. Specify dose, interval, duration.',
    input_schema: {
        type: 'object',
        properties: {
            model_name: { type: 'string' },
            dose: { type: 'number' },
            interval: { type: 'number', description: 'Dosing interval in hours' },
            n_doses: { type: 'number' },
        },
        required: ['dose', 'interval'],
    },
};
export async function simulateRegimen(args) {
    return { success: true, message: 'Simulation completed (stub)', plot_file: 'simulation.png' };
}
export const populationSimulationTool = {
    name: 'population_simulation',
    description: 'Simulate a population of virtual subjects with inter-individual variability.',
    input_schema: {
        type: 'object',
        properties: {
            model_name: { type: 'string' },
            n_subjects: { type: 'number' },
            dose: { type: 'number' },
        },
        required: ['n_subjects', 'dose'],
    },
};
export async function populationSimulation(args) {
    return { success: true, message: `Population simulation: ${args.n_subjects} subjects (stub)` };
}
//# sourceMappingURL=simulation.js.map