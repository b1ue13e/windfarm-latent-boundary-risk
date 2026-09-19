# Top-Tier Conference Teaser Figure (Figure 1) Guide & TikZ Templates

在顶会（NeurIPS/ICLR/ICML）中，**Figure 1 (Teaser Figure)** 决定了审稿人对论文的第一印象。优秀的 Figure 1 必须在一张图中直观展现：
1. **现有范式的困境 (Status Quo / Failure Mode)**
2. **我们的几何/机理突破 (Our Mechanism / Paradigm Shift)**
3. **关键优势对比 (Lead Time / Robustness Payoff)**

---

## 🎨 Figure 1 视觉对比设计法则

```
+-----------------------------------------------------------------------------------+
|  (a) Conventional Heuristics (Point-wise / Time-domain)                           |
|      Trajectory x(t) ---> [ Late / Missed Warning at Critical Bifurcation t* ]    |
|                                                                                   |
|  (b) Our Generic Framework Paradigm (Manifold & Spectral Gap)                     |
|      Tangent Bundle T_x M ---> [ Preemptive Spectral Collapse at t* - \Delta t ]   |
+-----------------------------------------------------------------------------------+
```

---

## 📄 可直接在 LaTeX 中编译的 TikZ 矢量代码

将以下代码置于 LaTeX 正文的第 1 页或第 2 页顶部：

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[scale=0.9, >=stealth, font=\small]

% Subfigure (a): Traditional Failure
\begin{scope}[shift={(0,0)}]
    \draw[thick, fill=red!5, rounded corners=8pt] (-0.5,-1.2) rectangle (7.5, 3.2);
    \node[anchor=north west, font=\bfseries\color{red!70!black}] at (-0.3, 3.0) {(a) Traditional Time-Domain / Statistical EWs};
    
    % Trajectory
    \draw[->, thick, gray] (0,0) -- (7,0) node[right] {$t$};
    \draw[->, thick, gray] (0,0) -- (0,2.5) node[above] {$x(t)$};
    
    \draw[thick, blue!70!black, smooth] plot coordinates {(0.5,0.4) (1.5,0.6) (2.5,0.5) (3.5,0.8) (4.5,0.7) (5.5,1.8) (6.5,2.4)};
    
    % Critical transition
    \draw[dashed, red, thick] (5.5,-0.2) -- (5.5, 2.5) node[above, font=\footnotesize] {Critical Shift $t^*$};
    \draw[fill=red] (5.5,1.8) circle (2.5pt);
    \node[anchor=south west, red!80!black, font=\footnotesize] at (5.5, 1.8) {Warning Triggered (Too Late!)};
\end{scope}

% Subfigure (b): Our Generic Framework Metric
\begin{scope}[shift={(8.5,0)}]
    \draw[thick, fill=blue!5, rounded corners=8pt] (-0.5,-1.2) rectangle (7.5, 3.2);
    \node[anchor=north west, font=\bfseries\color{blue!70!black}] at (-0.3, 3.0) {(b) Ours: Generic Project Framework (\texttt{OursMethod})};
    
    % Axis
    \draw[->, thick, gray] (0,0) -- (7,0) node[right] {$t$};
    \draw[->, thick, gray] (0,0) -- (0,2.5) node[above] {Spectral Gap $\gamma(t)$};
    
    % Spectral gap curve collapsing early
    \draw[thick, teal!80!black, smooth] plot coordinates {(0.5,2.2) (1.5,2.1) (2.5,1.9) (3.5,0.9) (4.5,0.2) (5.5,0.05) (6.5,0.02)};
    
    % Early Warning Trigger
    \draw[dashed, teal, thick] (3.5,-0.2) -- (3.5, 2.5) node[above, font=\footnotesize] {$t_{\mathrm{warn}}$};
    \draw[fill=teal] (3.5,0.9) circle (2.5pt);
    
    % Lead time interval indicator
    \draw[<->, thick, orange!90!black] (3.5,-0.6) -- (5.5,-0.6) node[midway, below, font=\bfseries\footnotesize] {Early Lead Time $\Delta t$};
    \draw[dashed, red, thick] (5.5,-0.2) -- (5.5, 1.2);
    \node[anchor=south west, blue!80!black, font=\footnotesize] at (3.5, 0.9) {Early Warning!};
\end{scope}

\end{tikzpicture}
\caption{\textbf{Conceptual Overview of the Generic Project Framework Paradigm.} 
(a) Conventional point-wise or statistical variance indicators only spike when the macroscopic state is already undergoing irreversible transition ($t^*$). 
(b) Our method monitors the Riemannian spectral gap $\gamma(t)$, which undergoes sharp collapse well in advance ($t_{\mathrm{warn}}$), providing a certified early warning window $\Delta t$ before systemic collapse.}
\label{fig:teaser_overview}
\end{figure*}
```

