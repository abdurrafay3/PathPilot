import { Router, type IRouter } from "express";
import healthRouter from "./health";
import routeRouter from "./route";

const router: IRouter = Router();

router.use(healthRouter);
router.use(routeRouter);

export default router;
