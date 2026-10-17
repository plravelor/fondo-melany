/*
  CONFIGURACIÓN DE LA CAMPAÑA — EDITAR SOLO LOS VALORES ENTRE COMILLAS.
  OPCIÓN A (SOLO GITHUB): deja sheetId: "" y modifica recaudadoManual al recibir aportes.
  OPCIÓN B (GOOGLE SHEETS): escribe el ID de la hoja pública en sheetId.
  En ambos casos se usa recaudadoManual como respaldo si Google no responde.
*/
window.CAMPANA = {
  nombre: "Melany Queeman",
  meta: 3000000,
  recaudadoManual: 200000,
  sheetId: "1rE9LvUukh7YXdpd8P_TtiSOU3Tnu0rZUTXZGsXWDhhU",
  sheetName: "PUBLICO",
  fechas: "19–24 de octubre de 2026",
  primerHito: 500000,
  hitos: [500000, 1000000, 2000000, 3000000],
  bancos: [
    { nombre: "Nequi", dato: "3023845409", tipo: "Número Nequi" },
    { nombre: "Bre-B · Nequi", dato: "@3023845409", tipo: "Llave Bre-B" },
    { nombre: "Bancolombia", dato: "348-202228-32", tipo: "Cuenta de ahorros" },
    { nombre: "Bre-B · Bancolombia", dato: "@melany179", tipo: "Llave Bre-B" }
  ]
};
