//! Interactive terminal UI frontend, built on `ratatui`/`crossterm`.
//!
//! Always compiled in and Android/Termux compatible (no windowing
//! dependencies) — usable by agents and humans alike. See [`crate::cli`]
//! for the scriptable, one-shot counterpart.

use std::io;
use std::time::Duration;

use crossterm::event::{self, Event, KeyCode};
use crossterm::execute;
use crossterm::terminal::{EnterAlternateScreen, LeaveAlternateScreen, disable_raw_mode, enable_raw_mode};
use ratatui::Terminal;
use ratatui::backend::CrosstermBackend;
use ratatui::widgets::{Block, Borders, Paragraph};

pub fn run() {
    enable_raw_mode().expect("failed to enable raw mode");
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen).expect("failed to enter the alternate screen");
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend).expect("failed to create the terminal");

    loop {
        terminal
            .draw(|frame| {
                let block = Block::default().title("outram-park").borders(Borders::ALL);
                let paragraph =
                    Paragraph::new("TUI frontend scaffold — press 'q' to quit.").block(block);
                frame.render_widget(paragraph, frame.area());
            })
            .expect("failed to draw the frame");

        if let Ok(true) = event::poll(Duration::from_millis(250)) {
            if let Ok(Event::Key(key)) = event::read() {
                if key.code == KeyCode::Char('q') {
                    break;
                }
            }
        }
    }

    disable_raw_mode().expect("failed to disable raw mode");
    execute!(terminal.backend_mut(), LeaveAlternateScreen).expect("failed to leave the alternate screen");
}
